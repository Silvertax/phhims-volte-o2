#!/usr/bin/env python3
# Patches PhhIms' bytecode (krazey/ims a3fec01). Each fix was found in a tester's radio log.
#
# v0.3.3, stuck call screen: the network answers an outgoing call (200 OK) but no RTP arrives
# within 2 s, or the other side hangs up before any RTP arrived. PhhIms ends the dialog and
# reports the cancellation with only the SIP Call-ID. PhhMmTelFeature matches it to the outgoing
# call only if it already knows that Call-ID, which it learns when the call is reported as
# progressing or connected. Neither has happened in this case, so the cancellation is taken for an
# unknown incoming call ("No IMS call listener for cancellation ... not falling back"), Android is
# never told, and the call screen stays on "dialing" until a reboot. Fix: both cancellation maps
# carry "outgoingCall" = "true", as PhhIms already does for a local CANCEL
# (SipRemoteDialogTermination.localCancelExtras), so PhhMmTelFeature routes the cancellation to
# the outgoing call and calls callSessionTerminated().
# Source equivalent: patches/0003-report-no-media-outgoing-end.patch.
#
# v0.3.4, other phone stays in the call: when the user hangs up an incoming call first, PhhIms
# writes the BYE on the TCP flow the INVITE arrived on, i.e. from the UE's protected server port
# (port_us) to the P-CSCF's client port (port_pc). TS 33.203 has the UE send requests from port_uc
# to port_ps; VIVACOM's P-CSCF silently drops the BYE (no response at all), so the other side
# stays in the call. BYEs for outgoing calls already go over the main flow (port_uc -> port_ps)
# and are answered with 200 OK. Fix: SipRemoteDialogTermination.localDialogRequestWriter always
# returns the main outbound flow (mainSipWriterForOutbound, which reopens a dormant flow).
# Source equivalent: patches/0004-local-bye-on-main-flow.patch.
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


def die(msg):
    sys.stderr.write("patch-phhims-dex: %s\n" % msg)
    sys.exit(1)


def add_outgoing_call_flag(arr, regs):
    """v0.3.3: adds "outgoingCall" to "true" to a 4-entry mapOf(...) literal."""

    def edit(body, signature):
        if '"outgoingCall"' in body:
            return None
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
        return body.replace(call, extra + call)

    return edit


# The original body after the parameter check: incoming ?: registered ?: fallback()
BYE_WRITER_OLD = """    .line 12
    if-nez p1, :cond_12

    if-nez p2, :cond_10

    invoke-interface {p3}, Lkotlin/jvm/functions/Function0;->invoke()Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Ljava/io/OutputStream;

    goto :goto_13

    :cond_10
    move-object v0, p2

    goto :goto_13

    :cond_12
    move-object v0, p1

    :goto_13
    return-object v0
"""

BYE_WRITER_NEW = """    .line 12
    invoke-interface {p3}, Lkotlin/jvm/functions/Function0;->invoke()Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Ljava/io/OutputStream;

    return-object v0
"""


def bye_on_main_flow(body, signature):
    """v0.3.4: localDialogRequestWriter returns fallbackWriter() only."""
    if BYE_WRITER_NEW in body and "if-nez p1" not in body:
        return None
    if body.count(BYE_WRITER_OLD) != 1:
        die("unexpected body in " + signature)
    return body.replace(BYE_WRITER_OLD, BYE_WRITER_NEW)


# (smali file, method signature line, edit function)
EDITS = [
    (
        "me/phh/sip/SipOutgoingCallConnectionLogs.smali",
        ".method public final postAnswerRtpTimeoutCancellationExtras(Ljava/lang/String;)Ljava/util/Map;",
        add_outgoing_call_flag("v0", ("v1", "v2")),
    ),
    (
        "me/phh/sip/SipRemoteEndExtrasBuilder.smali",
        ".method public final build(Ljava/lang/String;Ljava/lang/String;ZZZ)Ljava/util/Map;",
        add_outgoing_call_flag("v1", ("v0", "v2")),
    ),
    (
        "me/phh/sip/SipRemoteDialogTermination.smali",
        ".method public final localDialogRequestWriter(Ljava/io/OutputStream;Ljava/io/OutputStream;"
        "Lkotlin/jvm/functions/Function0;)Ljava/io/OutputStream;",
        bye_on_main_flow,
    ),
]


def patch_file(text, signature, edit):
    start = text.find(signature)
    if start < 0:
        die("method not found: " + signature)
    end = text.find(".end method", start)
    body = edit(text[start:end], signature)
    if body is None:
        return None
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

        # Each edit is independent: an APK that already has some of them gets the rest.
        changed = 0
        for rel, signature, edit in EDITS:
            path = os.path.join(out_dir, rel)
            if not os.path.exists(path):
                die("class not in %s: %s" % (target, rel))
            with open(path) as f:
                text = f.read()
            new = patch_file(text, signature, edit)
            if new is None:
                continue
            with open(path, "w") as f:
                f.write(new)
            changed += 1
        if changed == 0:
            print("patch-phhims-dex: already patched")
            sys.exit(3)

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
    print("patch-phhims-dex: patched %s (%d of %d methods)" % (target, changed, len(EDITS)))


if __name__ == "__main__":
    main()
