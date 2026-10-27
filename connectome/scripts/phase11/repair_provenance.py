"""One audited metadata-only repair; never rewrites legacy checkpoint contracts."""
from .common import ROOT,BASE,read,sha,sources

REPAIR = BASE/'repairs/calibration_freeze_v1'
CERTIFICATE_SHA256 = 'd1ef87836afd5189c7455498762322fc2f10a1dc3b11c5a601f3447faf4c3f5a'


def original_path(name):
    path=ROOT/name
    if not path.exists() and name.startswith('connectome/Results/phase'):
        path=ROOT/name.replace('connectome/Results/phase','connectome/phase',1)
    return path


def require_compatible_sources(recorded_sources,*artifacts):
    """Accept only exact legacy sources/artifacts covered by the tested repair."""
    certificate_path=REPAIR/'compatibility_certificate.json'
    if sha(certificate_path)!=CERTIFICATE_SHA256:
        raise ValueError('Repair compatibility certificate changed')
    certificate=read(certificate_path)
    approval=read(REPAIR/'approval.json')
    current=sources()
    if (approval.get('status')!='APPROVED_POST_TESTS' or approval.get('certificate_sha256')!=CERTIFICATE_SHA256
            or approval.get('new_sources_sha256')!=current):
        raise ValueError('Current sources have no tested repair approval')
    if recorded_sources!=certificate['legacy_sources_sha256']:
        raise ValueError('Unregistered legacy source set')
    for name,old in recorded_sources.items():
        expected=certificate['approved_changed_existing_sources'].get(name,old)
        if current.get(name)!=expected:
            raise ValueError('Repair changed an unapproved source')
    for name,value in certificate['frozen_bindings_sha256'].items():
        if sha(original_path(name))!=value:
            raise ValueError('Frozen scientific configuration/manifest changed')
    if not artifacts:
        raise ValueError('Repair compatibility requires specific bound artifacts')
    for path in artifacts:
        name=str(path.relative_to(ROOT))
        if name not in certificate['legacy_artifacts_sha256'] or sha(path)!=certificate['legacy_artifacts_sha256'][name]:
            raise ValueError('Unregistered or changed legacy artifact')
