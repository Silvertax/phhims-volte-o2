#!/usr/bin/env python3
# Patches PhhIms' bytecode so that an outgoing call PhhIms ends for lack of media is reported to
# Android as ended (v0.3.3, 2026-11-13).
#
# The fault (krazey/ims a3fec01, seen on a tester's phone): the network answers an outgoing call
# (200 OK) but no RTP arrives within 2 s, or the other side hangs up before any RTP arrived. PhhIms
# ends the dialog and reports the cancellation with only the SIP Call-ID. PhhMmTelFeature matches
# it to the outgoing call only if it already knows that Call-ID, which it learns when the call is
# reported as progressing or connected. Neither has happened in this case, so the cancellation is
# taken for an unknown incoming call ("No IMS call listener for cancellation ... not falling back"),
# Android is never told, and the call screen stays on "dialing" until a reboot; hanging up does
# nothing ("terminateCall without currentCall or pending outgoing INVITE").
#
# The fix adds "outgoingCall" = "true" to both cancellation maps, as PhhIms already does for a
# local CANCEL (SipRemoteDialogTermination.localCancelExtras). PhhMmTelFeature then routes the
# cancellation to the outgoing call (outgoingCall && outgoingCallSipCallId == null) and calls
# callSessionTerminated(). Source equivalent: patches/0003-report-no-media-outgoing-end.patch.
#
#   SMALI_DIR=dir/with/baksmali,smali,dexlib2,...jars tools/patch-phhims-dex.py in.apk out.apk
#
# Exit 0: patched, 3: already patched (out.apk not written), anything else: error.
import os
import re
import subprocess
import sys
import tempfile
import zipfile

CLASS_DESC = b"Lme/phh/sip/SipOutgoingCallConnectionLogs;"

# (smali file, method signature line, array register, (pair reg, value reg))
EDITS = [
    (
        "me/phh/sip/SipOutgoingCallConnectionLogs.smali",
        ".method public final postAnswerRtpTimeoutCancellationExtras(Ljava/lang/String;)Ljava/util/Map;",
        "v0",
        ("v1", "v2"),
    ),
    (
        "me/phh/sip/SipRemoteEndExtrasBuilder.smali",
        ".method public final build(Ljava/lang/String;Ljava/lang/String;ZZZ)Ljava/util/Map;",
        "v1",
        ("v0", "v2"),
    ),
]


def die(msg):
    sys.stderr.write("patch-phhims-dex: %s\n" % msg)
    sys.exit(1)


def patch_method(text, signature, arr, regs):
    start = text.find(signature)
    if start < 0:
        die("method not found: " + signature)
    end = text.find(".end method", start)
    body = text[start:end]
    if '"outgoingCall"' in body:
        return None
    # The map literal: a 4-element Pair array passed to MapsKt.mapOf
    size = re.compile(r"const/4 %s, 0x4(\s+)new-array %s, %s, \[Lkotlin/Pair;" % (arr, arr, arr))
    if len(size.findall(body)) != 1:
        die("array allocation not found exactly once in " + signature)
    body = size.sub(r"const/4 %s, 0x5\1new-array %s, %s, [Lkotlin/Pair;" % (arr, arr, arr), body)
    call = "    invoke-static {%s}, Lkotlin/collections/MapsKt;->mapOf([Lkotlin/Pair;)Ljava/util/Map;" % arr
    if body.count(call) != 1:
        die("mapOf call not found exactly once in " + signature)
    key, val = regs
    extra = (
        '    const-string %s, "outgoingCall"\n\n'
        '    const-string %s, "true"\n\n'
        "    invoke-static {%s, %s}, Lkotlin/TuplesKt;->to(Ljava/lang/Object;Ljava/lang/Object;)Lkotlin/Pair;\n\n"
        "    move-result-object %s\n\n"
        "    const/4 %s, 0x4\n\n"
        "    aput-object %s, %s, %s\n\n"
    ) % (key, val, key, val, key, val, key, arr, val)
    body = body.replace(call, extra + call)
    return text[:start] + body + text[end:]


def main():
    if len(sys.argv) != 3:
        die("usage: SMALI_DIR=... patch-phhims-dex.py in.apk out.apk")
    src, dst = sys.argv[1], sys.argv[2]
    smali_dir = os.environ.get("SMALI_DIR")
    if not smali_dir:
        die("set SMALI_DIR to a directory with the baksmali/smali 2.5.2 jars and their dependencies")
    cp = os.pathsep.join(
        os.path.join(smali_dir, f) for f in sorted(os.listdir(smali_dir)) if f.endswith(".jar")
    )

    with zipfile.ZipFile(src) as zin:
        dexes = [n for n in zin.namelist() if re.fullmatch(r"classes\d*\.dex", n)]
        target = [n for n in dexes if CLASS_DESC in zin.read(n)]
        if len(target) != 1:
            die("expected the class in exactly one dex, found %r" % target)
        target = target[0]
        dex = zin.read(target)

    with tempfile.TemporaryDirectory() as tmp:
        dex_in = os.path.join(tmp, "in.dex")
        with open(dex_in, "wb") as f:
            f.write(dex)
        out_dir = os.path.join(tmp, "smali")
        subprocess.run(["java", "-cp", cp, "org.jf.baksmali.Main", "d", "-o", out_dir, dex_in], check=True)

        changed = 0
        for rel, signature, arr, regs in EDITS:
            path = os.path.join(out_dir, rel)
            with open(path) as f:
                text = f.read()
            new = patch_method(text, signature, arr, regs)
            if new is None:
                continue
            with open(path, "w") as f:
                f.write(new)
            changed += 1
        if changed == 0:
            print("patch-phhims-dex: already patched")
            sys.exit(3)
        if changed != len(EDITS):
            die("only %d of %d methods needed the patch, refusing a partial patch" % (changed, len(EDITS)))

        dex_out = os.path.join(tmp, "out.dex")
        # API 33 keeps the dex format at 039, like the original
        subprocess.run(["java", "-cp", cp, "org.jf.smali.Main", "a", "--api", "33", "-o", dex_out, out_dir],
                       check=True)
        with open(dex_out, "rb") as f:
            new_dex = f.read()

    # Rewrite the APK with the new dex. The old signature is dropped (v2/v3 live outside the zip
    # entries, v1 files are skipped); build.sh aligns and re-signs the result.
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            if re.fullmatch(r"META-INF/[^/]+\.(SF|RSA|DSA|EC|MF)", info.filename):
                continue
            data = new_dex if info.filename == target else zin.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zout.writestr(zi, data)
    print("patch-phhims-dex: patched %s (%d methods)" % (target, changed))


if __name__ == "__main__":
    main()
