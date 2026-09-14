"""Merge JUnit runs, retaining the latest result for each module/test pair."""

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def merge_reports(inputs, output):
    cases = {}
    total_time = 0.0
    timestamp = ""
    for path in inputs:
        root = ET.parse(path).getroot()
        for suite in root.iter('testsuite'):
            total_time += float(suite.get('time', '0'))
            timestamp = timestamp or suite.get('timestamp', '')
        for case in root.iter('testcase'):
            properties = case.find('properties')
            if properties is None:
                properties = ET.SubElement(case, 'properties')
            ET.SubElement(properties, 'property', name='result_source', value=path.name)
            cases[(case.get('classname'), case.get('name'))] = case
    suite = ET.Element('testsuite', name='latest-per-case-results',
                       tests=str(len(cases)), timestamp=timestamp, time=f'{total_time:.3f}')
    for tag, attribute in (('failure', 'failures'), ('error', 'errors'), ('skipped', 'skipped')):
        suite.set(attribute, str(sum(case.find(tag) is not None for case in cases.values())))
    properties = ET.SubElement(suite, 'properties')
    ET.SubElement(properties, 'property', name='report_type',
                  value='Consolidated latest results: full run plus targeted follow-up; not one clean rerun of every case.')
    suite.extend(cases.values())
    wrapper = ET.Element('testsuites')
    wrapper.append(suite)
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(wrapper).write(output, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', type=Path, help='XML inputs in chronological order')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    merge_reports(args.inputs, args.output)
