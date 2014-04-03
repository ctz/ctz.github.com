---
layout: post
title: "Android keystore key leakage between security domains"
subtitle: ""
category: 
published: false
tags: [mobile, security, apps, android, keystore, key management]
---

* TOC
{:toc #toc-side}

A bug in Android's keystore service means private keys stored by one app
can be leaked to other apps, in violation of the guarantees the keystore
service makes to apps.

This bug affects all Android devices from ICS (4.0) onwards.  Devices with
a lock PIN, passphrase or pattern enabled are not affected: setting one
is the recommended work-around.

# Timeline

 *   **2014-02-24 AM** - Discovery.
 *   **2014-02-24 PM** - Vendor notification.
 *   **2014-02-24 PM** - Vendor acknowledgement and confirmation.
 *   **2014-02-26** - Attempt to setup coordinated disclosure (no response).
 *   **2014-04-03** - Public disclosure.

# Background

The keystore service offers key storage and use facilities to apps.  It
segregates apps by their Linux user id (uid), with the fundamental aim
that one app's keys are never available to another[^sep].  The keystore
service can be backed by software crypto, or a crypto module running
inside a TEE or SE.

[^sep]: "Android now offers a custom Java Security Provider in the KeyStore
        facility, called Android Key Store, which allows you to generate and save
        private keys that may be seen and used by only your app"

*[TEE]: trusted execution environment
*[SE]: secure element

The keystore has the concept of being *uninitialised*, *locked*, or
*unlocked*.  If the device has no device-level lock (like a pattern, pin,
or passphrase lockscreen) the keystore is uninitialised.  Otherwise, the
keystore is locked on phone boot, and unlocked when the lockscreen is
passed.

Keys stored on the behalf of apps can be encrypted at rest, but this
facility is not available when the keystore service is running in
uninitialised mode.  Other facilities (key generation and use)
are generally available in uninitialised and unlocked modes.

## UID allocation

Android's package manager service allocates uids by package on
installation, from a space between uid 10000 and 19999.  Resources owned
by a package's uid are removed during uninstallation, strictly before the
package manager considers that uid for reuse.  But, in general, the
package manager avoids immediate reuse of a uid (say, for an immediate
uninstall/install cycle).  The state used for this reuse avoidance is lost
when the device is rebooted.

When uninstalling a package, the package manager informs the keystore of
its uid, so that it can delete keys belonging to it (the `clear_uid`
function).  This is so the keystore does not leak keys owned by one app,
with another installed later is coincidentally assigned the same uid.

# Bug

Unfortunately a logic or design error in the keystore means for a keystore in the
uninitialised state, `clear_uid` does nothing[^walkthrough].  Keys belonging to an
uninstalled app are left on storage.

[^walkthrough]:
    See [keystore.cpp][keystorecpp]:
    
    1. No PIN/pattern means `isKeystoreUnlocked()` returns false (line 2319);
       the keystore is in `STATE_UNINITIALIZED`.
    2. `generate()` and `import()` work in `STATE_UNINITIALIZED`, as long as you do
       not ask for `KEYSTORE_FLAG_ENCRYPTED` (line 1727).
    3. pm, on uninstall or clear data, calls down to `clear_uid()`. But this
       does nothing in `STATE_UNINITIALIZED` (line 2239).

[keystorecpp]: https://android.googlesource.com/platform/system/security/+/9ffe9be8dd27def3f674da90cf9619437e3d428c/keystore/keystore.cpp

The implications of this are three-fold (in order of ascending severity):

 * *Storage leak*: the keys are left on disk forever.
 * *Privacy*: 'Clear data' for apps which use the keystore does not delete
   keys.  Malicious apps can therefore persist data here outside
   the control of the user (like advertising identifiers, etc.)
 * *Security*: an app which uses the keystore uncontrollably leaks keys to
   apps which later reuse its uid.

-----

# POC

Here are two trivial apps with source. [keystore_generate][ksgen] generates an
RSA key using `AndroidKeyStore` (the JCE KeyStore provide backed by the Android
keystore service). [keystore_list][kslist] lists whatever keys it
finds in its keystore: by definition, this app should never list any keys.

[ksgen]: https://github.com/ctz/android-keystore/tree/master/gen
[kslist]: https://github.com/ctz/android-keystore/tree/master/list

Steps to reproduce:

 1. Install `keystore_generate`, and run it.  It will print its uid, and
    generate a key.  Note down the uid.
 2. Uninstall `keystore_generate`, reinstall and and run it again.  Repeat
    this step a few times, noting down the uids.
 3. Uninstall `keystore_generate`.
 4. Reboot phone.  This resets the starting point for `pm`'s free uid search.
 5. Install and run `keystore_list`.  Note that:
    1. the uid it reports are those you noted occupied[^uidclash] by `keystore_generate` earlier,
    2. and keys it reports are ones actually belonging to `keystore_generate`.

The expected and correct behaviour is that `keystore_list` always reports
'found 0 keys' even if the uid is reused.

[^uidclash]: UID reuse like this is not a problem in and of itself, and is by design.
             Reuse is necessary to reproduce this bug though.  You may need another
             uninstall/reinstall cycle to select the next uid if you don't get a clash.

-----

# Patch 

[This patch][patch] means the keystore `clear_uid` function always makes an attempt to delete keys
belonging to a uid irrespective of the keystore's state.

    diff --git a/keystore/keystore.cpp b/keystore/keystore.cpp
    index 987e306..afa611d 100644
    --- a/keystore/keystore.cpp
    +++ b/keystore/keystore.cpp
    @@ -2235,12 +2235,6 @@ public:
                 return ::PERMISSION_DENIED;
             }
     
    -        State state = mKeyStore->getState(callingUid);
    -        if (!isKeystoreUnlocked(state)) {
    -            ALOGD("calling clear_uid in state: %d", state);
    -            return state;
    -        }
    -
             if (targetUid64 == -1) {
                 targetUid = callingUid;
             } else if (!is_granted_to(callingUid, targetUid)) {

[patch]: https://github.com/ctz/android-keystore/blob/master/keystore-key-leak.patch

-----

# Comments

This and issue [61989][issue-61989] makes me think the behaviour over various
lockscreen settings for keystore hasn't been fully thought about.
Particularly, it's very surprising and unhelpful to delete all the keys
belonging to apps when the user changes any lockscreen setting (even from
'None' to 'None'!).

[issue-61989]: https://code.google.com/p/android/issues/detail?id=61989

-----


