#!/usr/bin/env python3
from datetime import datetime
import json
import os
import re
import argparse
import csv
import copy
import sys
import gzip

strptime = datetime.strptime

class attriObject:
    """Class object for attribute parser."""
    def __init__(self, string):
        self.value = re.split(":", string)
        self.title = self.value[-1]

    def getElement(self, json_object):
        found = [json_object]
        for entry in self.value:
            for index in range(len(found)):
                try:
                    found[index] = found[index][entry]
                except (TypeError, KeyError):
                    print("'{0}' is not a valid json entry.".format(":".join(self.value)))
                    sys.exit()

                #If single search object is a list, search entire list. Error if nested lists.
                if isinstance(found[index], list):
                    if len(found) > 1:
                        raise Exception("Extractor currently does not handle nested lists.")
                    found = found[index]

        if len(found) == 0:
            return "NA"
        elif len(found) == 1:
            return found[0]
        else:
            return ";".join(found)

def json_entries(string, path):
    """Iterates over entries in path."""
    for filename in os.listdir(path):
        if re.match(string, filename) and ".json" in filename:
            f = gzip.open if ".gz" in filename else open
            print("parsing", filename)
            with f(path + filename, 'rb') as data_file:
                for line in data_file:
                    try:
                        json_object = json.loads(line.decode("utf-8"))
                    except ValueError:
                        print("Error in", filename, "entry incomplete.")
                        continue

                    if isinstance(json_object, list):
                        for jobject in json_object:
                            yield jobject
                    else:
                        yield json_object

def parse(args):
    with open(args.output, 'w+', encoding="utf-8") as output:
        csv_writer = csv.writer(output, dialect=args.dialect)
        csv_writer.writerow([a.title for a in args.attributes])
        count = 0
        tweets = set()

        for json_object in json_entries(args.string, args.path):

            #Check for duplicates
            identity = json_object['id']
            if identity in tweets:
                continue
            tweets.add(identity)

            #Check for time restrictions.
            if args.start or args.end:
                tweet_time = strptime(json_object['created_at'],'%a %b %d %H:%M:%S +0000 %Y')
                if args.start and args.start > tweet_time:
                    continue
                if args.end and args.end < tweet_time:
                    continue

            #Check for hashtag.
            if args.hashtag:
                for entity in json_object['entities']["hashtags"]:
                    if entity['text'].lower() == args.hashtag:
                        break
                else:
                    continue

            #Write this tweet to csv.
            item = [i.getElement(json_object) for i in args.attributes]
            csv_writer.writerow(item)

            count += 1

        print("Searched", len(tweets), "tweets and recorded", count, "items.")
        print("largest id:", max(tweets))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extracts attributes from tweets.')
    parser.add_argument("attributes", nargs='*', help="Attributes to search for. Attributes inside nested inside other attributes should be seperated by a colon. Example: user:screen_name, entities:hashtags:text.")
    parser.add_argument("-dialect", default="excel", help="Sets dialect for csv output. Defaults to excel. See python module csv.list_dialects()")
    parser.add_argument("-string", default="", help="Regular expression for files to parse. Defaults to empty string.")
    parser.add_argument("-path", default="./", help="Optional path to folder containing tweets. Defaults to current folder.")
    parser.add_argument("-output", default="output.csv", help="Optional file to output results. Defaults to output.csv.")
    parser.add_argument("-start", default="", help="Define start date for tweets. Format (mm:dd:yyyy)")
    parser.add_argument("-end", default="", help="Define end date for tweets. Format (mm:dd:yyyy)")
    parser.add_argument("-hashtag", default="", help="Define a hashtag that must be in parsed tweets.")
    args = parser.parse_args()

    if not args.path.endswith("/"):
        args.path += "/"

    args.start = strptime(args.start, '%m:%d:%Y') if args.start else False
    args.end = strptime(args.end, '%m:%d:%Y') if args.end else False
    args.attributes = [attriObject(i) for i in args.attributes]
    args.string = re.compile(args.string)
    args.hashtag = args.hashtag.lower()

    parse(args)
