"""Check detection boundaries without changing legitimate scientific text."""
import subprocess
from audit_text import audit_string, audit_paths, audit_git


def test_invisible_bidi_and_encoding_damage_are_errors():
    source = 'word' + chr(0x200B) + chr(0x202E) + chr(0xFFFD)
    findings = audit_string(source, 'sample')
    assert len([item for item in findings if item['severity'] == 'error']) == 3
    assert any(item['rule'] == 'bidirectional_control' for item in findings)


def test_scientific_symbols_and_disclosures_are_not_signatures():
    source = 'AUROC ' + chr(0x2212) + ' 0.05; ' + chr(0x2014) + ' range\n'
    source += 'Model: openai/whisper-base\n'
    source += 'Declaration of ' + 'generative AI use\n'
    findings = audit_string(source, 'sample')
    assert findings and all(item['severity'] == 'info' for item in findings)


def test_tool_markers_and_automatic_trailers_are_detected():
    trailer = 'Co-' + 'authored-by: ' + 'Codex <example@example.invalid>'
    marker = '<' + 'oai-mem-citation' + '>'
    findings = audit_string(trailer+'\n'+marker, 'sample')
    assert {item['rule'] for item in findings if item['severity'] == 'error'} == {'automatic_attribution', 'tool_marker'}


def test_secret_files_and_symlinks_are_not_read(tmp_path):
    (tmp_path/'.env').write_bytes(b'\xff')
    (tmp_path/'gitlab.env').write_bytes(b'\xff')
    (tmp_path/'credential.key').write_bytes(b'\xff')
    (tmp_path/'valid.txt').write_text('valid')
    (tmp_path/'link.txt').symlink_to(tmp_path/'.env')
    findings, scanned = audit_paths([tmp_path])
    assert scanned == 1 and findings == []


def test_non_nfc_spelling_is_reported_without_rewriting(tmp_path):
    source = 'e' + chr(0x0301)
    path = tmp_path/'text.txt'
    path.write_text(source)
    findings, _ = audit_paths([path])
    assert any(item['rule'] == 'non_nfc_text' for item in findings)
    assert path.read_text() == source


def test_commit_messages_are_audited(tmp_path):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    subprocess.run(['git','-C',str(tmp_path),'config','user.name','Test Author'],check=True)
    subprocess.run(['git','-C',str(tmp_path),'config','user.email','test@example.invalid'],check=True)
    message = 'Test\n\nCo-' + 'authored-by: ' + 'Codex <example@example.invalid>'
    subprocess.run(['git','-C',str(tmp_path),'commit','--allow-empty','-q','-m',message],check=True)
    assert any(item['rule'] == 'automatic_attribution' for item in audit_git(tmp_path))
