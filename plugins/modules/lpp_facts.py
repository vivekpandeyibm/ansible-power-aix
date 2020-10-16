#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020- IBM, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
author:
- AIX Development Team (@pbfinley1911)
module: lpp_facts
short_description: Returns installed software products as facts
description:
- Returns information about installed filesets or fileset updates.
version_added: '2.9'
requirements:
- AIX >= 7.1 TL3
- Python >= 2.7
options:
  filesets:
    description:
    - Specifies the names of software products.
    - Pattern matching characters, such as C(*) (asterisk) and C(?) (question mark), are valid.
    type: list
    elements: str
  bundle:
    description:
    - Specifies a file or bundle to use as the fileset list source.
    type: str
  path:
    description:
    - Specifies an alternate install location.
    type: str
  base_levels_only:
    description:
    - Limits listings to base level filesets (no updates returned).
    type: bool
    default: no
'''

EXAMPLES = r'''
- name: Populate fileset facts with the installation state for the most recent
        level of installed filesets for all of the bos.rte filesets
  lpp_facts:
    filesets: bos.rte.*
- debug:
    var: ansible_facts.filesets

- name: Populate fileset facts with the installation state for all the filesets
        contained in the Server bundle
  lpp_facts:
    bundle: Server
- debug:
    var: ansible_facts.filesets
'''

RETURN = r'''
ansible_facts:
  description:
  - Facts to add to ansible_facts about the installed software products on the system
  returned: always
  type: complex
  contains:
    filesets:
      description:
      - List of installed software products
      returned: success
      type: list
      elements: dict
      contains:
        name:
          description:
          - Fileset name
          returned: always
          type: str
          sample: "devices.scsi.disk.rte"
        level:
          description:
          - Fileset level
          returned: always
          type: str
          sample: "7.2.3.0"
        vrmf:
          description:
          - Fileset vrmf
          returned: always
          type: dict
          sample: "vrmf: { ver: 7, rel: 2, mod: 3, fix: 0 }"
        state:
          description:
          - State of the fileset on the system
          - C(applied) specifies that the fileset is installed on the system.
          - C(applying) specifies that an attempt was made to apply the specified
            fileset, but it did not complete successfully, and cleanup was not performed.
          - C(broken) specifies that the fileset or fileset update is broken and should be
            reinstalled before being used.
          - C(committed) specifies that the fileset is installed on the system.
          - C(efixlocked) specifies that the fileset is installed on the system and is
            locked by the interim fix manager.
          - C(obsolete) specifies that the fileset was installed with an earlier version
            of the operating system but has been replaced by a repackaged (renamed)
            newer version.
          - C(committing) specifies that an attempt was made to commit the specified
            fileset, but it did not complete successfully, and cleanup was not performed.
          - C(rejecting) specifies that an attempt was made to reject the specified
            fileset, but it did not complete successfully, and cleanup was not performed.
          returned: always
          type: str
        ptf:
          description:
          - Program temporary fix
          returned: when available
          type: str
        type:
          description:
          - Fileset type
          - C(install) specifies install image (base level).
          - C(maintenance) specifies maintenance level update.
          - C(enhancement).
          - C(fix).
          returned: always
          type: str
        description:
          description:
          - Fileset description
          returned: always
          type: str
        emgr_locked:
          description:
          - Specifies whether fileset is locked by the interim fix manager
          returned: always
          type: bool
        source:
          description:
          - Source path
          returned: always
          type: str
          sample: "/etc/objrepos"
'''

from ansible.module_utils.basic import AnsibleModule


LPP_TYPE = {
    'I': 'install',
    'M': 'maintenance',
    'E': 'enhancement',
    'F': 'fix'
}


def main():
    module = AnsibleModule(
        argument_spec=dict(
            filesets=dict(type='list', elements='str'),
            bundle=dict(type='str'),
            path=dict(type='str'),
            base_levels_only=dict(type='bool', default=False)
        ),
        mutually_exclusive=[
            ['filesets', 'bundle'],
        ],
        supports_check_mode=True
    )

    lslpp_path = module.get_bin_path('lslpp', required=True)

    cmd = [lslpp_path, '-lacq']
    if module.params['base_levels_only']:
        cmd += ['-I']
    if module.params['path']:
        cmd += ['-R', module.params['path']]
    if module.params['bundle']:
        cmd += ['-b', module.params['bundle']]
    elif module.params['filesets']:
        cmd += module.params['filesets']
    else:
        cmd += ['all']
    ret, stdout, stderr = module.run_command(cmd)
    # Ignore errors as lslpp might return 1 with -b

    # List of fields returned by lslpp -lac:
    # Source:Fileset:Level:PTF Id:State:Type:Description:EFIX Locked
    filesets = []
    for line in stdout.splitlines():
        raw_fields = line.split(':')
        if len(raw_fields) < 8:
            continue
        fields = [field.strip() for field in raw_fields]

        fileset = {}
        fileset['source'] = fields[0]
        fileset['name'] = fields[1]
        fileset['level'] = fields[2]
        vrmf = fields[2].split('.')
        if len(vrmf) == 4:
            fileset['vrmf'] = {
                'ver': int(vrmf[0]),
                'rel': int(vrmf[1]),
                'mod': int(vrmf[2]),
                'fix': int(vrmf[3])
            }
        if fields[3]:
            fileset['ptf'] = fields[3]
        fileset['state'] = fields[4].lower()
        if fields[5]:
            fileset['type'] = LPP_TYPE.get(fields[5], '')
        fileset['description'] = fields[6]

        if fields[7] == 'EFIXLOCKED':
            fileset['emgr_locked'] = True

        filesets.append(fileset)

    results = dict(ansible_facts=dict(filesets=filesets))

    module.exit_json(**results)


if __name__ == '__main__':
    main()
