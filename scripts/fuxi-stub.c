/*
 * Weak stubs for native symbols that UniXNU's XNU patches reference even when the
 * matching feature is switched off in the defconfig.
 *
 * Why this exists: patches/xnu add calls such as
 *   extern void native_legacy_display_probe(void); native_legacy_display_probe();
 * inside "#if DEVELOPMENT || DEBUG" blocks without also testing the feature macro,
 * so bsd_init.o references the symbol no matter what CONFIG_XNU_* says. The sheng
 * build always ships the archives that define them, so upstream never noticed.
 *
 * fuxi's bring-up build leaves those features off (no display archive, no
 * owner-trust chain, no boot progress), and they are unreachable anyway: each is
 * behind a boot argument that the fuxi payload does not pass. Defining them weak
 * keeps the link happy and lets a real archive override them later.
 */

#define FUXI_WEAK __attribute__((weak))

/* Display */
FUXI_WEAK void native_legacy_display_probe(void) {}
FUXI_WEAK void native_legacy_display_late_probe(void) {}

/* Boot progress */
FUXI_WEAK void boot_progress_poll(void) {}

/* Owner-root verified-root chain */
FUXI_WEAK const unsigned char verified_root_key[128] = { 0 };
FUXI_WEAK const unsigned char verified_root_policies[4096] = { 0 };
FUXI_WEAK const int verified_root_policy_count = 0;

FUXI_WEAK int vr_open(void) { return 0; }
FUXI_WEAK int vr_verify_block(void) { return 0; }
FUXI_WEAK int vr_xnu_crypto(void) { return 0; }

/* mockfs, in case the mockfs sources are not compiled into vfs_conf.o */
FUXI_WEAK int mockfs_mountroot(void) { return 0; }
FUXI_WEAK const unsigned char mockfs_vfsops[512] = { 0 };
FUXI_WEAK const unsigned char mockfs_vnodeop_opv_desc[512] = { 0 };
