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
# v0.3.6, speakerphone button does nothing: Telecom already switches a PhhIms call to
# MODE_IN_COMMUNICATION, then SipAudioRecordStarter sets the same mode again whenever the
# microphone starts. AudioService makes the most recent privileged requester the mode owner, and
# only the mode owner's communication device is applied: Telecom's setCommunicationDevice(speaker)
# was recorded but ignored ("preferredCommunicationDevice: null", seen in a tester's dumpsys audio;
# PhhIms does not run as the system UID here, so it is not the same client as Telecom). Fix: the
# mode is only set if it is not MODE_IN_COMMUNICATION already, as the downlink thread already does.
# Source equivalent: patches/0005-keep-telecom-audio-mode-owner.patch.
#
# v0.3.8, two ringback tones on outgoing calls: on every 180 Ringing without SDP, PhhIms reports
# the call as progressing with audio direction INACTIVE, which makes Telephony play its own
# ringback tone (ImsPhoneCall.isLocalTone). VIVACOM also sends its ringback tone as early media
# (RTP after the 183), which PhhIms plays, so the caller hears both. o2 and ONDO send no early
# media, so only the local tone plays there. Fix: the first early-media RTP frame of an outgoing
# call that carries speech (AMR FT 0-7, not SID or NO_DATA) is reported as progressing with
# "local-ringback" = "false", and later 180s of that call carry the same, so PhhMmTelFeature reports
# DIRECTION_SEND_RECEIVE and Telephony stops (or never starts) its tone. Without early media,
# nothing changes. Source equivalent: patches/0006-network-ringback-replaces-local.patch.
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


MODE_SET_OLD = """    const/4 v1, 0x3

    invoke-virtual {p2, v1}, Landroid/media/AudioManager;->setMode(I)V
"""

MODE_SET_NEW = """    const/4 v1, 0x3

    if-eq v0, v1, :phh_mode_already_set

    invoke-virtual {p2, v1}, Landroid/media/AudioManager;->setMode(I)V

    :phh_mode_already_set
"""


def keep_mode_owner(body, signature):
    """v0.3.6: setMode(MODE_IN_COMMUNICATION) only if the mode (v0) is not 3 already."""
    # smali renames labels, so a patched APK shows :cond_N instead of :phh_mode_already_set
    if re.search(r"const/4 v1, 0x3\s+if-eq v0, v1, :\w+\s+invoke-virtual \{p2, v1\}, "
                 r"Landroid/media/AudioManager;->setMode", body):
        return None
    if body.count(MODE_SET_OLD) != 1 or 'move-result v0\n\n    .line 17\n    .local v0, "previousAudioMode":I' not in body:
        die("unexpected body in " + signature)
    return body.replace(MODE_SET_OLD, MODE_SET_NEW)


# v0.3.8: helpers added to SipHandler. phhEarlySpeechCallId is the Call-ID of the outgoing call
# whose early media already carried speech; Call-IDs are unique, so it needs no reset.
EARLY_FIELD_ANCHOR = ".field private onOutgoingCallProgressing:Lkotlin/jvm/functions/Function2;\n"
EARLY_FIELD = ".field private volatile phhEarlySpeechCallId:Ljava/lang/String;\n"

EARLY_METHODS = """
.method private final phhNoLocalRingbackExtras(Ljava/lang/String;)Ljava/util/Map;
    .registers 5

    new-instance v0, Ljava/util/LinkedHashMap;

    invoke-direct {v0}, Ljava/util/LinkedHashMap;-><init>()V

    const-string v1, "call-id"

    invoke-interface {v0, v1, p1}, Ljava/util/Map;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    const-string v1, "early-media"

    const-string v2, "true"

    invoke-interface {v0, v1, v2}, Ljava/util/Map;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    const-string v1, "local-ringback"

    const-string v2, "false"

    invoke-interface {v0, v1, v2}, Ljava/util/Map;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    return-object v0
.end method

.method private final phhMaybeReportEarlySpeech(Lme/phh/sip/SipHandler$Call;I)V
    .registers 7

    invoke-virtual {p1}, Lme/phh/sip/SipHandler$Call;->getOutgoing()Z

    move-result v0

    if-eqz v0, :phh_done

    iget-object v0, p0, Lme/phh/sip/SipHandler;->callStarted:Ljava/util/concurrent/atomic/AtomicBoolean;

    invoke-virtual {v0}, Ljava/util/concurrent/atomic/AtomicBoolean;->get()Z

    move-result v0

    if-nez v0, :phh_done

    if-ltz p2, :phh_done

    const/4 v0, 0x7

    if-gt p2, v0, :phh_done

    invoke-virtual {p1}, Lme/phh/sip/SipHandler$Call;->getCallHeaders()Ljava/util/Map;

    move-result-object v0

    const-string v1, "call-id"

    invoke-interface {v0, v1}, Ljava/util/Map;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Ljava/util/List;

    if-eqz v0, :phh_done

    invoke-interface {v0}, Ljava/util/List;->isEmpty()Z

    move-result v1

    if-nez v1, :phh_done

    const/4 v1, 0x0

    invoke-interface {v0, v1}, Ljava/util/List;->get(I)Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Ljava/lang/String;

    if-eqz v0, :phh_done

    iget-object v1, p0, Lme/phh/sip/SipHandler;->phhEarlySpeechCallId:Ljava/lang/String;

    invoke-virtual {v0, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-nez v1, :phh_done

    iput-object v0, p0, Lme/phh/sip/SipHandler;->phhEarlySpeechCallId:Ljava/lang/String;

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "Outgoing early media carries audio; network ringback replaces the local tone callId="

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    const-string v2, "PHH SipHandler"

    invoke-static {v2, v1}, Landroid/telephony/Rlog;->d(Ljava/lang/String;Ljava/lang/String;)I

    iget-object v1, p0, Lme/phh/sip/SipHandler;->onOutgoingCallProgressing:Lkotlin/jvm/functions/Function2;

    if-eqz v1, :phh_done

    invoke-direct {p0, v0}, Lme/phh/sip/SipHandler;->phhNoLocalRingbackExtras(Ljava/lang/String;)Ljava/util/Map;

    move-result-object v2

    new-instance v3, Ljava/lang/Object;

    invoke-direct {v3}, Ljava/lang/Object;-><init>()V

    invoke-interface {v1, v3, v2}, Lkotlin/jvm/functions/Function2;->invoke(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    :phh_done
    return-void
.end method

.method private final phhProgressExtras(Ljava/util/Map;)Ljava/util/Map;
    .registers 4

    const-string v0, "call-id"

    invoke-interface {p1, v0}, Ljava/util/Map;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v0

    if-eqz v0, :phh_keep

    iget-object v1, p0, Lme/phh/sip/SipHandler;->phhEarlySpeechCallId:Ljava/lang/String;

    invoke-virtual {v0, v1}, Ljava/lang/Object;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-eqz v1, :phh_keep

    new-instance v0, Ljava/util/LinkedHashMap;

    invoke-direct {v0, p1}, Ljava/util/LinkedHashMap;-><init>(Ljava/util/Map;)V

    const-string v1, "local-ringback"

    const-string p1, "false"

    invoke-interface {v0, v1, p1}, Ljava/util/Map;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    return-object v0

    :phh_keep
    return-object p1
.end method

.method private final phhRecheckEarlySpeech(Lkotlin/jvm/functions/Function2;Ljava/util/Map;)V
    .registers 6

    const-string v0, "local-ringback"

    invoke-interface {p2, v0}, Ljava/util/Map;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v0

    const-string v1, "true"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v0

    if-eqz v0, :phh_done

    const-string v0, "call-id"

    invoke-interface {p2, v0}, Ljava/util/Map;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Ljava/lang/String;

    if-eqz v0, :phh_done

    iget-object v1, p0, Lme/phh/sip/SipHandler;->phhEarlySpeechCallId:Ljava/lang/String;

    invoke-virtual {v0, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-eqz v1, :phh_done

    invoke-direct {p0, v0}, Lme/phh/sip/SipHandler;->phhNoLocalRingbackExtras(Ljava/lang/String;)Ljava/util/Map;

    move-result-object v1

    new-instance v2, Ljava/lang/Object;

    invoke-direct {v2}, Ljava/lang/Object;-><init>()V

    invoke-interface {p1, v2, v1}, Lkotlin/jvm/functions/Function2;->invoke(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    :phh_done
    return-void
.end method
"""


def early_media_helpers(text, rel):
    """v0.3.8: adds the phhEarlySpeechCallId field and the helper methods to SipHandler."""
    if EARLY_FIELD in text:
        return None
    if text.count(EARLY_FIELD_ANCHOR) != 1 or ".method private final phhMaybeReportEarlySpeech" in text:
        die("unexpected field layout in " + rel)
    # before the anchor: the anchor field's annotations follow its .field line
    text = text.replace(EARLY_FIELD_ANCHOR, EARLY_FIELD + "\n" + EARLY_FIELD_ANCHOR)
    return text.rstrip("\n") + "\n" + EARLY_METHODS


EARLY_RTP_OLD = """    :goto_7c
    move v11, v6
"""

EARLY_RTP_NEW = """    :goto_7c
    move v11, v6

    invoke-direct {p0, v5, v11}, Lme/phh/sip/SipHandler;->phhMaybeReportEarlySpeech(Lme/phh/sip/SipHandler$Call;I)V
"""


def early_rtp_hook(body, signature):
    """v0.3.8: every downlink RTP frame's FT (v11) goes to phhMaybeReportEarlySpeech; v5 is the call."""
    if "phhMaybeReportEarlySpeech" in body:
        return None
    if body.count(EARLY_RTP_OLD) != 1 or "move-object/from16 v5, p1" not in body:
        die("unexpected body in " + signature)
    return body.replace(EARLY_RTP_OLD, EARLY_RTP_NEW)


PROGRESS_OLD = """    invoke-virtual {v1}, Lme/phh/sip/OutgoingProgressNotification;->getExtras()Ljava/util/Map;

    move-result-object v14

    invoke-interface {v5, v13, v14}, Lkotlin/jvm/functions/Function2;->invoke(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
"""

PROGRESS_NEW = """    invoke-virtual {v1}, Lme/phh/sip/OutgoingProgressNotification;->getExtras()Ljava/util/Map;

    move-result-object v14

    invoke-direct {v0, v14}, Lme/phh/sip/SipHandler;->phhProgressExtras(Ljava/util/Map;)Ljava/util/Map;

    move-result-object v14

    invoke-interface {v5, v13, v14}, Lkotlin/jvm/functions/Function2;->invoke(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    invoke-direct {v0, v5, v14}, Lme/phh/sip/SipHandler;->phhRecheckEarlySpeech(Lkotlin/jvm/functions/Function2;Ljava/util/Map;)V
"""


def early_progress_hook(body, signature):
    """v0.3.8: a 180 of a call with audible early media asks for no local ringback; if the first
    speech frame arrived while the 180 was being reported, it is reported again (v0 is this)."""
    if "phhProgressExtras" in body:
        return None
    if body.count(PROGRESS_OLD) != 1 or "iget-object v5, v0, Lme/phh/sip/SipHandler;->onOutgoingCallProgressing" not in body:
        die("unexpected body in " + signature)
    return body.replace(PROGRESS_OLD, PROGRESS_NEW)


DIRECTION_OLD = """    .line 822
    const/4 v1, 0x0

    iput v1, v0, Landroid/telephony/ims/ImsStreamMediaProfile;->mAudioDirection:I
"""

DIRECTION_NEW = """    .line 822
    const/4 v1, 0x0

    const-string v2, "local-ringback"

    invoke-interface {p2, v2}, Ljava/util/Map;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v2

    const-string v3, "false"

    invoke-virtual {v3, v2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v2

    if-eqz v2, :phh_local_ringback

    const/4 v1, 0x3

    :phh_local_ringback
    iput v1, v0, Landroid/telephony/ims/ImsStreamMediaProfile;->mAudioDirection:I
"""


def ringback_direction(body, signature):
    """v0.3.8: DIRECTION_SEND_RECEIVE (3) instead of INACTIVE (0) when "local-ringback" is "false"."""
    if 'const-string v2, "local-ringback"' in body:
        return None
    if body.count(DIRECTION_OLD) != 1 or '"Outgoing call progressing: "' not in body:
        die("unexpected body in " + signature)
    return body.replace(DIRECTION_OLD, DIRECTION_NEW)


# HD test switch (test builds after v0.3.8): VIVACOM answers PhhIms' outgoing offer with AMR-NB
# although it lists AMR-WB first, while the same SIM gets HD on a stock phone. To find out what
# VIVACOM objects to without a new build per guess, persist.sys.phhims.wb_offer changes the offer
# at runtime (read at every outgoing call, bitmask, 0 or unset = unchanged):
#   1 = offer AMR-WB only (AMR-NB and telephone-event/8000 are left out)
#   2 = b=AS:49 instead of 88 (49 kbps is what stock phones send for AMR-WB)
#   3 = both
# Source equivalent: patches/0007-hd-offer-test-switch.patch.
WB_OFFER_OLD = """    :goto_56
    move v14, v0
"""

WB_OFFER_NEW = """    :goto_56
    move v14, v0

    if-eqz v12, :phh_wb_offer_done

    const-string v0, "persist.sys.phhims.wb_offer"

    const/4 v1, 0x0

    invoke-static {v0, v1}, Landroid/os/SystemProperties;->getInt(Ljava/lang/String;I)I

    move-result v0

    and-int/lit8 v1, v0, 0x1

    if-eqz v1, :phh_wb_offer_as

    const/4 v1, 0x2

    new-array v1, v1, [Ljava/lang/Integer;

    invoke-static {v9}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object v2

    const/4 v3, 0x0

    aput-object v2, v1, v3

    invoke-static {v11}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object v2

    const/4 v3, 0x1

    aput-object v2, v1, v3

    invoke-static {v1}, Lkotlin/collections/CollectionsKt;->listOf([Ljava/lang/Object;)Ljava/util/List;

    move-result-object v13

    :phh_wb_offer_as
    and-int/lit8 v1, v0, 0x2

    if-eqz v1, :phh_wb_offer_done

    const/16 v14, 0x31

    :phh_wb_offer_done
"""


def wb_offer_switch(body, signature):
    """HD test switch: persist.sys.phhims.wb_offer picks the tracks (v13) and b=AS (v14)."""
    if '"persist.sys.phhims.wb_offer"' in body:
        return None
    if body.count(WB_OFFER_OLD) != 1 or '"Outgoing INVITE codec offer: offerAmrWb="' not in body:
        die("unexpected body in " + signature)
    return body.replace(WB_OFFER_OLD, WB_OFFER_NEW)


NB_LINES_OLD = """    check-cast v9, Ljava/lang/Iterable;

    invoke-static {v1, v9}, Lkotlin/collections/CollectionsKt;->addAll(Ljava/util/Collection;Ljava/lang/Iterable;)Z

    .line 147
"""

NB_LINES_NEW = """    check-cast v9, Ljava/lang/Iterable;

    invoke-static {v2}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object v10

    invoke-interface {v7, v10}, Ljava/util/List;->contains(Ljava/lang/Object;)Z

    move-result v10

    if-eqz v10, :phh_skip_nb_lines

    invoke-static {v1, v9}, Lkotlin/collections/CollectionsKt;->addAll(Ljava/util/Collection;Ljava/lang/Iterable;)Z

    :phh_skip_nb_lines
    .line 147
"""


def nb_lines_follow_tracks(body, signature):
    """HD test switch: the AMR-NB rtpmap/fmtp lines are only written when the m= line offers AMR-NB
    (v7 = allTracks, v2 = amrNbTrack; v10 is dead here, the fmtp prefix was consumed above)."""
    if "Ljava/util/List;->contains(Ljava/lang/Object;)Z" in body:
        return None
    if body.count(NB_LINES_OLD) != 1 or '" telephone-event/8000"' not in body:
        die("unexpected body in " + signature)
    return body.replace(NB_LINES_OLD, NB_LINES_NEW)


# (smali file, method signature line or None for the whole class, edit function)
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
    (
        "me/phh/sip/SipAudioRecordStarter.smali",
        ".method public final startForImsUplink(Ljava/lang/String;Landroid/media/AudioManager;"
        "Landroid/media/AudioRecord;Landroid/media/MediaCodec;)Ljava/lang/Integer;",
        keep_mode_owner,
    ),
    # The helpers first: the hooks below call them.
    ("me/phh/sip/SipHandler.smali", None, early_media_helpers),
    (
        "me/phh/sip/SipHandler.smali",
        ".method private final handleReceivedDownlinkRtpPacket(Lme/phh/sip/SipHandler$Call;"
        "Ljava/net/DatagramPacket;[BILme/phh/sip/NegotiatedAudioCodec;"
        "Lme/phh/sip/SipDownlinkAudioDecoderWorker;)V",
        early_rtp_hook,
    ),
    (
        "me/phh/sip/SipHandler.smali",
        ".method private final handleOutgoingProgressOrFailureResponse(Lme/phh/sip/SipResponse;"
        "Ljava/lang/String;Ljava/util/concurrent/atomic/AtomicInteger;)Ljava/lang/Boolean;",
        early_progress_hook,
    ),
    (
        "me/phh/ims/PhhMmTelFeature$createCallSession$2$3.smali",
        ".method public final invoke(Ljava/lang/Object;Ljava/util/Map;)V",
        ringback_direction,
    ),
    (
        "me/phh/sip/SipOutgoingInviteSdp.smali",
        ".method private final buildMediaOffer(Ljava/lang/String;Z)Lme/phh/sip/OutgoingInviteSdpMediaOffer;",
        wb_offer_switch,
    ),
    (
        "me/phh/sip/SipOutgoingInviteSdp.smali",
        ".method private final buildGenericBody(Ljava/net/DatagramSocket;Lme/phh/sip/OutgoingInviteSdpMediaOffer;"
        "Ljava/lang/String;Ljava/lang/String;ZZ)[B",
        nb_lines_follow_tracks,
    ),
]


def patch_file(text, signature, edit, rel):
    if signature is None:
        return edit(text, rel)
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

    # Each class lives in exactly one dex (me.phh.sip in one, me.phh.ims in another here).
    with zipfile.ZipFile(src) as zin:
        dexes = {n: zin.read(n) for n in zin.namelist() if re.fullmatch(r"classes\d*\.dex", n)}
    owner = {}
    for rel, _, _ in EDITS:
        desc = ("L%s;" % rel[: -len(".smali")]).encode()
        # Other dexes may reference the class too; it is defined where baksmali writes its file.
        found = [n for n, data in dexes.items() if desc in data]
        if not found:
            die("class not in any dex: " + rel)
        owner[rel] = found

    new_dexes = {}
    changed = 0
    with tempfile.TemporaryDirectory() as tmp:
        candidates = sorted({n for found in owner.values() for n in found})
        out_dirs = {}
        for name in candidates:
            dex_in = os.path.join(tmp, name)
            with open(dex_in, "wb") as f:
                f.write(dexes[name])
            out_dirs[name] = os.path.join(tmp, name + ".smali")
            subprocess.run(["java", "-cp", cp, "org.jf.baksmali.Main", "d", "-o", out_dirs[name], dex_in],
                           check=True)

        # Each edit is independent: an APK that already has some of them gets the rest.
        touched = set()
        for rel, signature, edit in EDITS:
            homes = [n for n in owner[rel] if os.path.exists(os.path.join(out_dirs[n], rel))]
            if len(homes) != 1:
                die("expected %s defined in exactly one dex, found %r" % (rel, homes))
            path = os.path.join(out_dirs[homes[0]], rel)
            with open(path) as f:
                text = f.read()
            new = patch_file(text, signature, edit, rel)
            if new is None:
                continue
            with open(path, "w") as f:
                f.write(new)
            touched.add(homes[0])
            changed += 1
        if changed == 0:
            print("patch-phhims-dex: already patched")
            sys.exit(3)

        for name in sorted(touched):
            dex_out = os.path.join(tmp, name + ".out")
            # API 33 keeps the dex format at 039, like the original
            subprocess.run(["java", "-cp", cp, "org.jf.smali.Main", "a", "--api", "33", "-o", dex_out,
                            out_dirs[name]], check=True)
            with open(dex_out, "rb") as f:
                new_dexes[name] = f.read()

    # Rewrite the APK with the new dexes. The old signature is dropped (v2/v3 live outside the zip
    # entries, v1 files are skipped); build.sh aligns and re-signs the result.
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            if re.fullmatch(r"META-INF/[^/]+\.(SF|RSA|DSA|EC|MF)", info.filename):
                continue
            data = new_dexes.get(info.filename) or zin.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zout.writestr(zi, data)
    print("patch-phhims-dex: patched %s (%d of %d edits)" % (", ".join(sorted(new_dexes)), changed, len(EDITS)))


if __name__ == "__main__":
    main()
