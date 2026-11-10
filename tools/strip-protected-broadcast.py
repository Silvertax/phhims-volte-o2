#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Remove the <protected-broadcast> declaration from the PhhIms APK manifest.

Why: PhhIms refreshes its IMS registration from an alarm that delivers the
broadcast me.phh.ims.ALARM_PERIODIC_REGISTER through a PendingIntent, and its
manifest declares that action as a protected broadcast. Android only lets the
system UIDs send protected broadcasts. Upstream PhhIms runs as
android.uid.system, so that works. The build used by this module has no
sharedUserId (it cannot be platform-signed), so ActivityManager rejects the
alarm's broadcast ("Permission Denial: not allowed to send broadcast ..."),
the alarm is never re-armed and the registration is never refreshed. Once it
expires, calls fall back to 2G until something forces a new registration.

Without the declaration the action is an ordinary broadcast. PhhIms registers
its receiver with RECEIVER_NOT_EXPORTED, so still only PhhIms itself (and the
system) can deliver it.

Usage: strip-protected-broadcast.py IN.apk OUT.apk

Only AndroidManifest.xml changes; every other entry is copied byte for byte in
the original order. OUT.apk is unaligned and unsigned: run zipalign and
apksigner on it afterwards (build.sh does).

Exit status: 0 = element removed and OUT.apk written,
             3 = IN.apk declares no protected broadcast (OUT.apk not written).
"""
import struct
import sys
import zipfile

RES_STRING_POOL = 0x0001
RES_XML = 0x0003
RES_XML_START_ELEMENT = 0x0102
RES_XML_END_ELEMENT = 0x0103
UTF8_FLAG = 0x100
TARGET = "protected-broadcast"


def read_string_pool(chunk):
    _type, header_size, _size, count, _styles, flags, strings_start, _styles_start = struct.unpack_from(
        "<HHIIIIII", chunk, 0
    )
    utf8 = bool(flags & UTF8_FLAG)
    strings = []
    for i in range(count):
        pos = strings_start + struct.unpack_from("<I", chunk, header_size + 4 * i)[0]
        if utf8:
            # UTF-16 length, then UTF-8 byte length; each one or two bytes
            if chunk[pos] & 0x80:
                pos += 2
            else:
                pos += 1
            n = chunk[pos]
            pos += 1
            if n & 0x80:
                n = ((n & 0x7F) << 8) | chunk[pos]
                pos += 1
            strings.append(chunk[pos:pos + n].decode("utf-8", "replace"))
        else:
            n = struct.unpack_from("<H", chunk, pos)[0]
            pos += 2
            if n & 0x8000:
                n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", chunk, pos)[0]
                pos += 2
            strings.append(chunk[pos:pos + 2 * n].decode("utf-16-le", "replace"))
    return strings


def strip_manifest(axml):
    """Return (new_axml, removed_count)."""
    xml_type, header_size, total = struct.unpack_from("<HHI", axml, 0)
    if xml_type != RES_XML or total != len(axml):
        raise ValueError("AndroidManifest.xml is not a binary XML document")

    out = [axml[:header_size]]
    strings = None
    removed = 0
    depth = 0
    drop_end = False  # the next END_ELEMENT belongs to a removed element
    pos = header_size
    while pos < total:
        ctype, _chsize, csize = struct.unpack_from("<HHI", axml, pos)
        if csize < 8 or pos + csize > total:
            raise ValueError("corrupt chunk at offset %d" % pos)
        chunk = axml[pos:pos + csize]
        pos += csize

        if ctype == RES_STRING_POOL and strings is None:
            strings = read_string_pool(chunk)
        elif ctype == RES_XML_START_ELEMENT:
            if drop_end:
                raise ValueError("<%s> has child elements; refusing to edit" % TARGET)
            name = strings[struct.unpack_from("<I", chunk, 20)[0]]
            depth += 1
            if name == TARGET and depth == 2:
                removed += 1
                drop_end = True
                continue
        elif ctype == RES_XML_END_ELEMENT:
            depth -= 1
            if drop_end:
                name = strings[struct.unpack_from("<I", chunk, 20)[0]]
                if name != TARGET:
                    raise ValueError("unexpected </%s> while removing <%s>" % (name, TARGET))
                drop_end = False
                continue
        out.append(chunk)

    if drop_end or depth != 0:
        raise ValueError("unbalanced elements in AndroidManifest.xml")
    body = b"".join(out)
    return body[:4] + struct.pack("<I", len(body)) + body[8:], removed


def main(argv):
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    src, dst = argv[1], argv[2]
    with zipfile.ZipFile(src) as zin:
        manifest, removed = strip_manifest(zin.read("AndroidManifest.xml"))
        if removed == 0:
            print("%s: no <%s> declaration, nothing to do" % (src, TARGET))
            return 3
        with zipfile.ZipFile(dst, "w") as zout:
            for item in zin.infolist():
                info = zipfile.ZipInfo(item.filename, item.date_time)
                info.compress_type = item.compress_type
                info.external_attr = item.external_attr
                info.create_system = item.create_system
                data = manifest if item.filename == "AndroidManifest.xml" else zin.read(item.filename)
                zout.writestr(info, data)
    print("%s: removed %d <%s> declaration(s) -> %s (unaligned, unsigned)" % (src, removed, TARGET, dst))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
