# PIN reset says no temporary PIN, but login still asks for the old PIN

**Repository** `kea3123-bit/ekeberadaansmkbbsul` — **branch** `refactor/performance-v2`  
**Production site** `https://kea3123-bit.github.io/ekeberadaansmkbbsul/`  
**Authoritative database after rollback** Google Sheets / bound Apps Script project.

## Cause and code fix

The old reset wrote to `user.row` from the shared users cache. If `PENGGUNA` was sorted/imported after this cache was populated, reset could target an unrelated row while sending a success email to the intended user. Also, cached account status could continue reporting PIN ready, and the code sent email without verifying that the target row was actually cleared.

Updated:
- `apps-script/40_UsersData.gs` — `getAllUsersFresh_()` and `getUserByEmailFresh_()` use the sheet directly; no cached row numbers.
- `apps-script/10_Auth.gs` — resolve the user's current row before reset, verify email on that row, clear PIN salt/hash and AuthType, set WajibTukarPassword, increment session version, flush and **read back** the actual row before sending the reset email.
- Account lookup, PIN login and first PIN setup now use current sheet state.
- `apps-script/tests/pin-reset-fresh-read.test.js` tests sorted rows, fresh login state, wrong-user protection and failed writes (no false success emails).

This patch is in GitHub **only** until the Apps Script Web App is redeployed. Nothing here resets or publishes the PHP/MySQL database.

## Make the fix live (required)

1. Open the **original Apps Script project bound to the Google Sheets used by the live website** (not a cloned project).
2. Replace **both** script files `10_Auth.gs` and `40_UsersData.gs` from the exact branch `refactor/performance-v2/apps-script/`. Save.
3. Choose **Deploy → Manage deployments → existing Web App → Edit (pencil) → Version: New version → Deploy**. Do not create an unrelated new deployment that changes the `/exec` URL.
4. Confirm the production bridge URL in `web/config.js` points to that exact deployed `/exec` URL.
5. As administrator, reset the affected user's PIN **one more time**. In sheet `PENGGUNA`, verify the row by email:
   - **J PasswordSalt:** blank
   - **K PasswordHash:** blank
   - **L WajibTukarPassword:** TRUE
   - **M VersiSesi:** incremented
   - **S AuthType:** blank
   Do not publish values from those cells, and do not edit anyone else's row.
6. On the user's browser choose **Bukan anda? Gunakan akaun DELIMa lain**, enter the same registered email and press **Teruskan**. It should open **Cipta PIN baharu** without requesting the old PIN.

If steps 5 and 6 disagree, check that the editor and deployed Apps Script Web App **both use the same bound Spreadsheet** and that the **existing deployment has actually been updated**. Merely saving in the editor does not update deployed Web Apps.

## Security

Do not send any PIN, hash, salt, user data, session token, or Google Apps Script Script Properties to GitHub or public logs. The reset affects only authentication columns of the intended account and revokes its previous sessions; it does **not** delete KEHADIRAN, TIDAK_HADIR or any punch records.
