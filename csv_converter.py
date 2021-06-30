#!/usr/bin/env python3

# Copyright (c) 2021, Justin D Holcomb (justin@justinholcomb.me) All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

################################################################################
#                                 Script Info                                  #
################################################################################

# Title:                    csv_converter.py
# Author:                   Justin D Holcomb (justin@justinholcomb.me)
# Created:                  June 28, 2021
# Version:                  0.0.1
# Requires:                 Python 3.6+ (fstrings)
# Description:              Converts a CSV from a source system, enriches the
#                             data, then exports to a destination CSV format.

################################################################################
#                                Import Modules                                #
################################################################################

from pathlib import Path
from os.path import exists
import argparse
import csv
import datetime
import json
import logging

################################################################################
#                                  Variables                                   #
################################################################################

ARGPARSE_DESCRIPTION = """
Converts a CSV from a source system, enriches the data, then exports to a
destination CSV format.

Requires:
    Python 3.6+
"""

# These are the headers in the CSV for the source file.
SOURCE_HEADERS = {
    "No",
    "Customer ID",
    "Company Name",
    "Flat Charge",
    "Current Volume",
    "Current Amount",
    "YTD Volume",
    "YTD Amount",
}

# These are the headers in the CSV for the mapping file.
MAPPING_HEADERS = {
    "Customer ID",
    "Company Name",
    "Account Number",
}

# This is the header name used to match an account from the two systems.
ACCOUNT_KEY = "Customer ID"

# Contains the source field name and what it needs to be renamed to.
FIELD_NAME_CHANGE = {
    "SOURCE_FIELD_NAME": "DESTINATION_FIELD_NAME",
}

# These are the headers in the CSV for the destination file (to the billing software).
BILLING_HEADERS = {
    "No",
    "Customer ID",
    "Company Name",
    "Account Number",
    "Flat Charge",
    "Current Volume",
    "Current Amount",
    "YTD Volume",
    "YTD Amount",
}
DEFAULT_SOURCE_CSV_FILENAME = "accounting.csv"
DEFAULT_MAPPING_CSV_FILENAME = "account_mapping.csv"
DEFAULT_DEST_CSV_FILENAME_PREFIX = "billing_"
DEFAULT_DEST_CSV_FILENAME = f"{DEFAULT_DEST_CSV_FILENAME_PREFIX}YYYYMMDD_HHMM.csv"

LOGGER = logging.getLogger(__name__)

################################################################################
#                                  Functions                                   #
################################################################################

def convert_formats(accounting_data, mapping_data):
    """
    This converts the original data and changes it to match the desired format
    for the destination system.
    """
    line_count = 0

    # Iterate over each line in source file.
    for row in accounting_data:
        line_count += 1
        LOGGER.info(f"Converting line {line_count}")

        ## Check if account number is in account mapping file.
        # If there is not a matching account number: prompt the user, immediately
        #   add it to the mapping file.
        if row[ACCOUNT_KEY] not in mapping_data.keys():
            row['Account Number'] = prompt_user_for_account(row['Customer ID'], row['Company Name'])
            mapping_data[row[ACCOUNT_KEY]] = {
                "Customer ID": row['Customer ID'],
                "Company Name": row['Company Name'],
                "Account Number": row['Account Number'],
            }
            write_csv(DEFAULT_MAPPING_CSV_FILENAME, MAPPING_HEADERS, mapping_data.values())
        else:
            row['Account Number'] = mapping_data[row[ACCOUNT_KEY]]['Account Number']

        # Rename source field names to match expected destination field names.
        for source_field, dest_field in FIELD_NAME_CHANGE.items():
            if source_field in row.keys():
                row[dest_field] = row[source_field]
                del row[source_field]

        # Add any special handling here. Such as splitting fields or other field specific processing.

    return accounting_data


def load_csv(filename, headers, load_as_dict=False):
    """
    Loads data from a CSV file. Can load data as an dictionary or as a list of
    dictionaries.
    """
    line_count = 0

    if load_as_dict:
        dataset = {}
    else:
        dataset = []

    with open(filename, encoding='utf-8-sig') as fp:
        csv_reader = csv.DictReader(
            fp,
            #fieldnames=headers,
            quoting=csv.QUOTE_ALL,
            lineterminator='\r\n',
            delimiter=','
        )

        for row in csv_reader:
            line_count += 1
            if load_as_dict:
                dataset[row[ACCOUNT_KEY]] = row
            else:
                dataset.append(row)
    LOGGER.info(f"Processed {line_count} lines from {filename}")

    return dataset


def prompt_user_for_account(id, name):
    """
    Prompts a user for input and returns the value.

    TODO: Add error handling and input validation.
    """
    return input(f"Please enter the account number for '{name}' aka ID {id}: ")


def write_billing_csv(data, user_filename):
    """
    This is a wrapper to the `write_csv()` function to calculate a filename with
    a timestamp.
    """

    # If a filename that is not the default, use that value. Otherwise calculate
    #   the filename.
    if user_filename == DEFAULT_DEST_CSV_FILENAME:
        DEFAULT_DEST_CSV_FILENAME_PREFIX
        timestamp = datetime.datetime.now()
        timestamp_string = timestamp.strftime("%Y%m%d_%H%M")
        filename = f"{DEFAULT_DEST_CSV_FILENAME_PREFIX}{timestamp_string}.csv"
    else:
        filename = user_filename

    write_csv(filename, BILLING_HEADERS, data)


def write_csv(filename, headers, dataset):
    """
    Writes data to a CSV file.
    """
    with open(filename, 'w') as fp:
        wr = csv.DictWriter(
            fp,
            fieldnames=headers,
            quoting=csv.QUOTE_ALL,
            lineterminator='\r\n',
            delimiter=','
        )
        wr.writeheader()
        wr.writerows(dataset)

    return True

################################################################################
#                                     Main                                     #
################################################################################

def parse_args():
    """
    Parses command line arguments.
    """

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=ARGPARSE_DESCRIPTION)
    parser.add_argument('--source-csv-filename',
                        dest="source_csv_filename",
                        help=f"CSV from water accounting system. Default: {DEFAULT_SOURCE_CSV_FILENAME}",
                        default=DEFAULT_SOURCE_CSV_FILENAME)
    parser.add_argument('--dest-csv-filename',
                        dest="dest_csv_filename",
                        help=f"CSV for the billing system. The default output is f{DEFAULT_DEST_CSV_FILENAME_PREFIX}_YYYYMMDD_HHMM.csv",
                        default=DEFAULT_DEST_CSV_FILENAME)
    parser.add_argument('-v',
                        dest="warn_logging",
                        help=f"Use WARNING level logging output.",
                        action="store_true",
                        default=False)
    parser.add_argument('-vv',
                        dest="info_logging",
                        help=f"Use INFO level logging output.",
                        action="store_true",
                        default=False)
    parser.add_argument('-vvv',
                        dest="debug_logging",
                        help=f"Use most verbose DEBUG level logging output.",
                        action="store_true",
                        default=False)
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    ''' When manually ran from command line. '''

    args = parse_args()

     # Setup logging.
    if args.debug_logging is True:
        LOGGER.setLevel(logging.DEBUG)
    elif args.info_logging is True:
        LOGGER.setLevel(logging.INFO)
    elif args.warn_logging is True:
        LOGGER.setLevel(logging.WARNING)
    else:
        LOGGER.setLevel(logging.ERROR)
    CH = logging.StreamHandler()
    FORMATTER = logging.Formatter("%(message)s")
    CH.setFormatter(FORMATTER)
    LOGGER.addHandler(CH)

    LOGGER.info(f"Loading water accounting data from: {args.source_csv_filename}")
    LOGGER.debug(f"Expecting water accounting data headers: {SOURCE_HEADERS}")
    this_months_data = load_csv(args.source_csv_filename, SOURCE_HEADERS)

    LOGGER.debug("Data from water accounting:")
    LOGGER.debug(json.dumps(this_months_data, indent=4))

    # Create mapping file if missing.
    if exists(DEFAULT_MAPPING_CSV_FILENAME) == False:
        LOGGER.error(f"Mapping file is missing, creating.")
        Path(DEFAULT_MAPPING_CSV_FILENAME).touch()

    # Load account mapping from CSV.
    LOGGER.info(f"Loading account mapping data from: {DEFAULT_MAPPING_CSV_FILENAME}")
    LOGGER.debug(f"Expecting account mapping headers: {MAPPING_HEADERS}")
    account_mapping = load_csv(DEFAULT_MAPPING_CSV_FILENAME, MAPPING_HEADERS, load_as_dict=True)

    LOGGER.debug("Data from account mapping:")
    LOGGER.debug(json.dumps(account_mapping, indent=4))

    # Process the water accounting CSV to the billing CSV.
    LOGGER.info("Converting CSV to destination format.")
    processed_data = convert_formats(this_months_data, account_mapping)

    # Write the billing data to a timestamped CSV.
    LOGGER.info("Writing converted data to CSV.")
    write_billing_csv(processed_data, args.dest_csv_filename)
