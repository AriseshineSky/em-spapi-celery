# -*- coding: utf-8 -*-

# Copyright © 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import sys
import fnmatch
import io
import csv

import click

from cmutils import logger


@click.command()
@click.option('-c', '--columns', default='1', help='Columns to extract, multiple column must be separate by comma.')
@click.option('-s', '--separator', default='\t', help='Column separator, default is tab.')
@click.option('-f', '--file_pattern', default='*.txt', help='File pattern to match, default is *.txt.')
@click.option('-r', '--reserve_header', is_flag=True, help='Whether to reserve header row.')
@click.option('-o', '--output_path', help='Result output path.')
@click.argument('input_path')
def extract_columns(columns, separator, file_pattern, reserve_header, output_path, input_path):
    if not input_path or not output_path:
        logger.error('input_path and output_path is required to run!')
        sys.exit(1)

    input_path = os.path.abspath(os.path.expanduser(input_path))
    if not os.path.exists(input_path):
        logger.error('Could not find input file or directory - %s', input_path)
        sys.exit(1)

    output_path = os.path.abspath(os.path.expanduser(output_path))
    output_dir = os.path.dirname(output_path)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    if os.path.isfile(output_path):
        os.remove(output_path)

    columns = sorted([int(c.strip()) for c in columns.split(',') if c.strip().isdigit()])

    files = []
    if os.path.isfile(input_path):
        files.append(input_path)
    else:
        for root, dirnames, filenames in os.walk(input_path):
            for filename in fnmatch.filter(filenames, file_pattern):
                files.append(os.path.join(root, filename))

    records = []
    for file_path in files:
        logger.info("Processing %s", file_path)
        with io.open(file_path, encoding='utf-8', errors='ignore') as fh:
            reader = csv.reader(fh, delimiter=separator)

            if not reserve_header:
                next(reader)

            for record in reader:
                field_cnt = len(record)
                if field_cnt < columns[-1]:
                    logger.info('[InvalidRecord] %s', record)
                    continue

                item = [record[col - 1] for col in columns]
                records.append('\t'.join(item))
        logger.info("Done %s", file_path)

    unique_records = list({}.fromkeys(records).keys())
    with io.open(output_path, 'w', encoding='utf-8', errors='ignore') as output_fh:
        output_fh.write("\n".join(unique_records))
        output_fh.write("\n")


if __name__ == '__main__':
    extract_columns()
