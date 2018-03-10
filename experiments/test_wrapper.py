#!/usr/bin/env python3

import argparse
import os
import math
from subprocess import check_call


DEFAULT_BANDWIDTHS = [i * 0.25 for i in range(1, 25)]
DEFAULT_DELAYS = [25, 50, 100, 200, 500]

SRC_DIR = os.path.dirname(os.path.realpath(__file__))
SCRIPTS_DIR = os.path.join(SRC_DIR, 'scripts')

CHROME_LOGGER_PATH = os.path.join(SCRIPTS_DIR, 'chrome_logger.py')
LOG_PARSER_PATH = os.path.join(SCRIPTS_DIR, 'video_log_parser.py')


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', type=str, help='Dash server url')
    parser.add_argument('outdir', type=str,
                        help="Directory to store parsed log output to")
    parser.add_argument('-bw', '--bandwidth', type=float, nargs='+',
                        default=DEFAULT_BANDWIDTHS,
                        help='Fixed bandwidths in Mbps')
    parser.add_argument('-d', '--delay', nargs='+', default=DEFAULT_DELAYS,
                        type=int, help='Fixed delays in ms')
    parser.add_argument('-n', type=int, default=1,
                        help='Number of trials')
    parser.add_argument('-t', '--duration', type=int, default=900,
                        help='Number of seconds to run the test')
    return parser.parse_args()


PACKET_SIZE = 1504
SCHEDULE_LEN = 100


def bw_to_schedule(mbps):
    pps = mbps * (10 ** 6) / (8.0 * PACKET_SIZE)
    packet_times = []
    accumulator = 0.0
    for i in range(SCHEDULE_LEN):
        accumulator += 1000.0 / pps
        packet_times.append(math.ceil(accumulator))
    return packet_times


def run_once(url, bw, delay, exp_num, duration, outdir):
    raw_out_path = os.path.join(outdir, '{}mbps-{}ms-{}.raw.log'.format(
                                bw, delay, exp_num))
    schedule_file = '/tmp/schedule-{}mbps-{}ms-{}'.format(bw, delay, exp_num)
    try:
        with open(schedule_file, 'w') as fp:
            for t in bw_to_schedule(bw):
                fp.write('{}\n'.format(t))
        chrome_cmd = [
            'mm-delay', str(delay),
            'mm-link', schedule_file, schedule_file,
            '--meter-downlink', '--meter-uplink',
            '--',
            CHROME_LOGGER_PATH,
            url,
            '-t', str(duration),
            '-o', raw_out_path
        ]
        check_call(chrome_cmd)
    finally:
        os.remove(schedule_file)

    parser_command = [LOG_PARSER_PATH, raw_out_path]
    parsed_out_path = os.path.join(outdir, '{}mbps-{}ms-{}.log'.format(
                                   bw, delay, exp_num))
    with open(parsed_out_path, 'w') as fp:
        check_call(parser_command, stdout=fp)


def main(url, outdir, bandwidth, delay, n, duration):
    if os.path.exists(outdir):
        raise Exception('Output path already exists')
    os.makedirs(outdir)

    num_experiments_left = n * len(bandwidth) * len(delay)
    print ('Running {} experiments: est {}s'.format(
           num_experiments_left, num_experiments_left * duration))

    for i in range(n):
        for bw in bandwidth:
            for d in delay:
                run_once(url, bw, d, i, duration, outdir)

                num_experiments_left -= 1
                print ('{} experiments remaining: est {}s'.format(
                       num_experiments_left, num_experiments_left * duration))


if __name__ == '__main__':
    main(**vars(get_args()))
