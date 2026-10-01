#!/usr/bin/env python3
"""
Retry a failed dvd/bluray job by first making a tolerant ddrescue copy of the
disc to an ISO, then running the normal MakeMKV -> HandBrake/FFmpeg pipeline
against that ISO instead of the raw device.

For a disc/drive combination that's marginal at a particular read (MakeMKV's
own retry logic gets stuck on one bad block instead of working around it),
ddrescue's retry-with-backoff/skip-and-revisit approach can succeed where a
straight MakeMKV rip hung or failed outright.

Only meaningful for a job that failed *during* MakeMKV's rip - identification
(title, disc type, track list) already happened during the original run and
is reused here rather than repeated. Launched by the UI (arm/ui/json_api.py::
rip_via_iso) as its own process, the same way udev launches arm/ripper/main.py
for a fresh rip.
"""
import argparse
import logging
import os
import sys
import time
from importlib.util import find_spec
from pathlib import Path

# If the arm module can't be found, add the folder this file is in to PYTHONPATH
# This is a bad workaround for non-existent packaging
if find_spec("arm") is None:
    sys.path.append(str(Path(__file__).parents[2]))

from arm.models.job import Job, JobState  # noqa: E402
from arm.models.system_drives import SystemDrives  # noqa: E402
from arm.ripper import arm_ripper, logger, makemkv, utils  # noqa: E402
from arm.ui import constants, db  # noqa: E402
from arm.ui.settings import DriveUtils as drive_utils  # noqa: E402

DRIVE_READY_RETRIES = 10
DRIVE_READY_POLL_SECONDS = 1


def entry():
    """Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(
        description='Retry a failed job by ddrescue-ing the disc to an ISO, then ripping from that')
    parser.add_argument('-j', '--job-id', type=int, required=True)
    return parser.parse_args()


def wait_for_disc(job, drive):
    """
    Poll the drive for a loaded, readable disc, since the disc has usually
    already been physically ejected by the time a failed job is retried
    (see arm.ripper.main's unconditional job.eject() on exit).\n
    :param job: Current job
    :param drive: arm.models.system_drives.SystemDrives row for job.devpath
    :raises RipperException: if no disc becomes ready in time. The exception
        is marked already_notified since a specific, actionable notification
        (insert the disc, retry) is sent here first.
    """
    for num in range(1, DRIVE_READY_RETRIES + 1):
        drive.tray_status()
        if drive.ready:
            return
        logging.info(f"[{num} of {DRIVE_READY_RETRIES}] Waiting for a disc in {job.devpath}.")
        time.sleep(DRIVE_READY_POLL_SECONDS)
    utils.notify(
        job, constants.NOTIFY_TITLE,
        f"Rip via ISO for '{job.title}' needs the disc back in {job.devpath}. "
        "Insert it and try again."
    )
    raise utils.RipperException(
        f"No disc found in {job.devpath} to rescue.", already_notified=True)


def rip_via_iso(job_id):
    """
    Rescue job_id's disc to an ISO with ddrescue, then rip/transcode from it\n
    :param job_id: id of a job whose disctype is dvd/bluray and RIPMETHOD is "mkv".
        The caller (json_api.rip_via_iso) is responsible for checking the job was in
        JobState.FAILURE before launching this script - by the time this function
        runs, the UI has already flipped job.status to ISO_RIPPING for immediate
        feedback, so re-checking for FAILURE here would always (harmlessly, but
        confusingly) fail. Same division of responsibility as retry_transcode.py.
    :return: None
    """
    job = Job.query.get(job_id)
    if job is None:
        raise utils.RipperException(f"No job found with id {job_id}")
    if job.disctype not in ("dvd", "bluray"):
        raise utils.RipperException(f"Rip via ISO only supports dvd/bluray jobs, not {job.disctype!r}")
    if job.config.RIPMETHOD != "mkv":
        raise utils.RipperException(
            "Rip via ISO only supports RIPMETHOD 'mkv' for now - this job is configured for "
            f"'{job.config.RIPMETHOD}'")

    log_file = logger.resume_job_log(job)
    logging.info(f"************* Rip via ISO: retrying job {job_id}: {job.title} *************")

    drive = SystemDrives.query.filter_by(mount=job.devpath).first()
    if drive is None:
        raise utils.RipperException(f"No drive found in the database for {job.devpath}")
    if drive.processing and drive.job_id_current != job.job_id:
        raise utils.RipperException(
            f"Drive {job.devpath} is currently busy with job {drive.job_id_current}. "
            "Wait until it's free, then retry.")

    wait_for_disc(job, drive)
    drive_utils.update_drive_job(job)

    iso_path = os.path.join(str(job.config.RAW_PATH), f"{job.title}.iso")
    utils.database_updater({'iso_path': iso_path, 'status': JobState.ISO_RIPPING.value}, job)
    utils.rescue_disc_to_iso(job, iso_path)

    # The physical disc has served its purpose - free the drive for the next job
    # while the rest of this one continues from the ISO.
    job.eject()
    db.session.commit()

    type_sub_folder = utils.convert_job_type(job.video_type)
    rawpath = makemkv.setup_rawpath(job, os.path.join(str(job.config.RAW_PATH), str(job.title)))
    utils.database_updater({'status': JobState.VIDEO_RIPPING.value}, job)
    try:
        makemkv.makemkv_mkv(job, rawpath, source=f"iso:{iso_path}", rescan=False)
    except Exception as mkv_error:
        utils.database_updater(
            {'status': JobState.FAILURE.value, 'errors': str(mkv_error)}, job)
        raise utils.RipperException("Error while running MakeMKV against the rescued ISO") from mkv_error

    # MakeMKV successfully extracted from the ISO - it's no longer needed
    utils.database_updater({'raw_path': rawpath, 'iso_path': None}, job)
    utils.delete_iso(iso_path)

    try:
        arm_ripper.start_transcode(job, log_file, rawpath, job.transcode_out_path, True)
    except Exception as transcode_error:
        utils.database_updater(
            {'status': JobState.TRANSCODE_FAILED.value, 'errors': str(transcode_error)}, job)
        raise

    arm_ripper.finish_visual_media(
        job, rawpath, job.transcode_out_path, job.path, type_sub_folder,
        use_make_mkv=True, makemkv_out_path=rawpath)


if __name__ == "__main__":
    args = entry()
    try:
        rip_via_iso(args.job_id)
    except Exception as error:
        already_notified = getattr(error, "already_notified", False)
        job = Job.query.get(args.job_id)
        if already_notified:
            # The raiser (e.g. wait_for_disc()) already sent the user a specific,
            # actionable notification - a second generic one would just be noise.
            logging.info(f"ARM is exiting: {error}")
        else:
            logging.critical("Rip via ISO failed.", exc_info=True)
            if job:
                utils.notify(
                    job, constants.NOTIFY_TITLE,
                    f"ARM failed to rip {job.title} via ISO. Check the logs for more details. {error}"
                )
        if job:
            # rip_via_iso()'s own except blocks already set a more specific status
            # (FAILURE for a MakeMKV/ISO failure, TRANSCODE_FAILED for a transcode
            # failure) and committed it - don't clobber that here. Otherwise (e.g. the
            # disc-wait timing out while status is still ISO_RIPPING/VIDEO_RIPPING),
            # fall back to FAILURE so the job doesn't get stuck in a non-terminal
            # state and the "Rip via ISO" button becomes available again.
            if job.status not in (JobState.FAILURE.value, JobState.TRANSCODE_FAILED.value):
                job.status = JobState.FAILURE.value
                job.errors = str(error)
                db.session.commit()
    else:
        job = Job.query.get(args.job_id)
        if job:
            job.status = JobState.SUCCESS.value
            db.session.commit()
