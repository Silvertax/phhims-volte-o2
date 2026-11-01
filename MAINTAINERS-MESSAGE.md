# Draft message for the PixelOS r8q maintainers

Not sent. Edit freely, then paste it into the r8q_cloud chat or send it to the maintainers directly. Replace `<repo link>` with the GitHub link.

---

Hi! Thanks for the PixelOS 17 build for the S20 FE, it's been running great for me. I know VoLTE isn't working on the build, and I wanted to see if I could get it going, so I'm sharing what worked in case it's useful for future builds.

**What I did:** I got VoLTE calls and SMS working on Airtel India using PhhIms (krazey/ims), the open-source userspace IMS app, with no vendor IMS blobs involved. I tested it on build 20261023 with a KernelSU kernel. IMS registers (200 OK), calls connect both ways with proper audio, data keeps working during the call, and SMS sends and receives. I've only tested it on one phone and one SIM, so please treat it as "worked for me", not as proven everywhere. Wi-Fi calling I haven't tried to fix.

**What was needed, in short:**
1. PhhIms in priv-app, with the right `privapp-permissions` entries. Your platform key is private, so I built it without `sharedUserId` and used the allowlist instead. In a proper ROM build you can just platform-sign it.
2. An overlay on the phone app setting `config_ims_mmtel_package` to `me.phh.ims`, plus VoLTE availability flags in the `android` overlay.
3. The carrier config for Airtel has no VoLTE flags, and the CarrierConfig app reads it from its assets, so my overlay was ignored. The fix was a few lines in PhhIms that apply a persistent carrier-config override on startup. A normal carrier-config entry in the ROM would do the same job.
4. Minor: a hidden-API whitelist, default runtime permissions, and a couple of small compile fixes (details in the repo).

I did all of this as a KernelSU module so nothing on the system partition changed. It has boot-loop protection, and disabling the module undoes everything.

**Everything is here:** <repo link>. It has the patch against upstream PhhIms (pinned commit), the module source, the overlay sources, a readme that explains how each part works, and a release zip if you want to try it on your own device. PhhIms is GPL-2.0, so the repo is too.

If you'd like to include it in the ROM, the readme has a short list of what the build needs. Happy to test builds, send logs, or answer questions. If anything looks wrong or I've misunderstood how your tree is set up, tell me and I'll fix it.

Thanks again for the work on this ROM!
