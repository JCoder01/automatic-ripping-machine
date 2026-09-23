#!/usr/bin/env python3
"""
Re-run MakeMKV's track scan for a job that's waiting on manual track selection,
using a caller-supplied minimum track length override for this job only (does not
change the site-wide MOVIE_MIN_LENGTH/SHOW_MIN_LENGTH/MINLENGTH defaults).

Launched by the UI (arm/ui/jobs/jobs.py::rescan_tracks) as its own process, the same
way udev launches arm/ripper/main.py for a fresh rip, since scanning talks to the
physical drive via MakeMKV.
"""
import argparse
import logging
import sys
from importlib.util import find_spec
from pathlib import Path

# If the arm module can't be found, add the folder this file is in to PYTHONPATH
# This is a bad workaround for non-existent packaging
if find_spec("arm") is None:
    sys.path.append(str(Path(__file__).parents[2]))

from arm.models.job import Job, JobState  # noqa: E402
from arm.models.track import Track  # noqa: E402
from arm.ripper import makemkv, utils  # noqa: E402
from arm.ui import db  # noqa: E402


def entry():
    """Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Rescan a disc with a different minimum track length')
    parser.add_argument('-j', '--job-id', type=int, required=True)
    parser.add_argument('-m', '--min-length', type=int, required=True)
    return parser.parse_args()


def rescan(job_id, min_length):
    """
    Re-run MakeMKV's disc info scan for job_id with an overridden minimum track
    length, replacing whatever tracks a previous scan found\n
    :param job_id: id of a job waiting for manual track selection
    :param min_length: minimum track length (seconds) to use for this rescan
    :return: None
    """
    job = Job.query.get(job_id)
    if job is None:
        raise utils.RipperException(f"No job found with id {job_id}")
    if not (job.manual_mode and job.status == JobState.MANUAL_WAIT_STARTED.value and not job.manual_start):
        raise utils.RipperException(f"Job {job_id} is not waiting for manual track selection")
    if job.drive is None or job.drive.mdisc is None:
        raise utils.RipperException(f"Job {job_id} has no known MakeMKV disc index to rescan")

    field = {"movie": "MOVIE_MIN_LENGTH", "series": "SHOW_MIN_LENGTH"}.get(job.video_type, "MINLENGTH")
    logging.info(f"Rescanning job {job_id} with {field}={min_length} (was {getattr(job.config, field)})")
    setattr(job.config, field, str(min_length))

    # Nothing has been ripped yet at this stage, so it's safe to drop the previous
    # scan's tracks and let get_track_info() repopulate them from scratch.
    Track.query.filter_by(job_id=job.job_id).delete()
    db.session.commit()

    makemkv.get_track_info(job.drive.mdisc, job)


if __name__ == "__main__":
    args = entry()
    try:
        rescan(args.job_id, args.min_length)
    except Exception:
        logging.critical("Track rescan failed.", exc_info=True)
