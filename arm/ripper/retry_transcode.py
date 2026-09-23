#!/usr/bin/env python3
"""
Retry the transcode step for a job whose MakeMKV rip already succeeded but whose
HandBrake/FFmpeg transcode failed (job.status == TRANSCODE_FAILED).

Re-transcodes from the raw files MakeMKV already left on disk (job.raw_path),
instead of re-ripping the physical disc. Launched by the UI (arm/ui/json_api.py::
retry_transcode) as its own process, the same way udev launches arm/ripper/main.py
for a fresh rip.
"""
import argparse
import logging
import os
import sys
from importlib.util import find_spec
from pathlib import Path

# If the arm module can't be found, add the folder this file is in to PYTHONPATH
# This is a bad workaround for non-existent packaging
if find_spec("arm") is None:
    sys.path.append(str(Path(__file__).parents[2]))

from arm.models.job import Job, JobState  # noqa: E402
from arm.ripper import arm_ripper, logger, utils  # noqa: E402
from arm.ui import constants, db  # noqa: E402


def entry():
    """Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Retry the transcode step for a previously ripped job')
    parser.add_argument('-j', '--job-id', type=int, required=True)
    return parser.parse_args()


def retry(job_id):
    """
    Re-run just the transcode step for job_id, then the usual post-processing\n
    :param job_id: id of a job with status TRANSCODE_FAILED and a valid raw_path
    :return: None
    """
    job = Job.query.get(job_id)
    if job is None:
        raise utils.RipperException(f"No job found with id {job_id}")
    if not job.raw_path or not os.path.isdir(job.raw_path):
        raise utils.RipperException(
            f"Raw ripped files for job {job_id} are no longer available at {job.raw_path!r}")

    log_file = logger.resume_job_log(job)
    logging.info(f"************* Retrying transcode for job {job_id}: {job.title} *************")

    type_sub_folder = utils.convert_job_type(job.video_type)
    # MakeMKV already ripped this job (that's why raw_path exists), so we know for
    # certain the mkv-sourced transcode path applies - pass protection=True so
    # arm_ripper.rip_with_mkv() takes that branch regardless of the original disc's
    # actual protection flag (which isn't persisted and doesn't matter any more).
    try:
        arm_ripper.start_transcode(job, log_file, job.raw_path, job.transcode_out_path, True)
    except Exception as transcode_error:
        utils.database_updater(
            {'status': JobState.TRANSCODE_FAILED.value, 'errors': str(transcode_error)}, job)
        raise

    arm_ripper.finish_visual_media(
        job, job.raw_path, job.transcode_out_path, job.path, type_sub_folder,
        use_make_mkv=True, makemkv_out_path=job.raw_path)


if __name__ == "__main__":
    args = entry()
    try:
        retry(args.job_id)
    except Exception as error:
        logging.critical("Retry of transcode step failed.", exc_info=True)
        job = Job.query.get(args.job_id)
        if job:
            utils.notify(
                job, constants.NOTIFY_TITLE,
                f"ARM failed to retry transcoding {job.title}. Check the logs for more details. {error}"
            )
            # retry()'s own except already marks a transcode-step failure as
            # TRANSCODE_FAILED (still retryable) and commits it - don't clobber that.
            # Anything else (job not found, raw files missing, post-processing failure)
            # falls back to a generic failure, matching main.py's top-level handler.
            if job.status != JobState.TRANSCODE_FAILED.value:
                job.status = JobState.FAILURE.value
                job.errors = str(error)
                db.session.commit()
