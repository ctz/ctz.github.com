+++
date = 2014-08-28
path = "2014/08/28/libotr-code-review"
template = "page.html"
title = "libotr: the code review"
extra = { toc = true }
tags = ["code", "review", "security", "libotr", "netsec"]
+++

Here's a review of [libotr][] I performed on a couple of long plane journeys recently.

# The source
The reviewed source is [this tree][master].  I passed all the source through `astyle`
[first][massage-commit].  This is intended to reveal any bugs hidden by formatting, and
fortunately also removes libotr's unconventional (but consistent) indentation[^1].
Line numbers given below are given for the processed source.

# The overview
libotr is *not* a travesty of confusion and neglect like [openssl][].  In fact, it
shows encouraging signs of being competently written.  But all software has bugs, and
everything can be improved.

In summary:

* The 'secure memory' allocation arena seems to have the classic [CWE-14][cwe-14] problem.
* There are a large number of unchecked mallocs/strdups.  This is at most a reliablity/DOS problem
  in normal environments, but if libotr is ever used in an embedded environment this can become 
  [arbitrary code execution][vector-rewrite][^2].  If you really squint.
* There is quite a lot of manual string manipulation.  I didn't find any overt errors here, but it's
  a worry for the future.
* There are some integer overflows, but none which seem to be dangerous because they have
  immensely impractical constraints.  However, I'd argue this is only fortuitous.

# Recommendations

## Allocate-or-die
There are a lot of calls to libgcrypt functions which have malloc-or-die semantics
(via `gcry_xmalloc` etc.).  This means libotr *as it stands* might just exit the process
under memory pressure.  This isn't a wonderful behaviour for a library, but is an improvement
over faulting or if application code can't be taught to handle errors.
  
I would suggest adopting `xmalloc` semantics for all existing malloc/strdup calls.

## String manipulation
Replace manual string manipulation with a higher-level interface.  For most uses in the library,
using a `xasprintf`-alike would be a vast improvement.

Original code:

```c
char *buf = malloc(strlen(OTR_ERROR_PREFIX) + strlen(err_msg) + 1);

if (buf) {
  strcpy(buf, OTR_ERROR_PREFIX);
  strcat(buf, err_msg);
  ops->inject_message(opdata, context->accountname,
                      context->protocol, context->username, buf);
  free(buf);
};
```

vs.

```c
char *buf = xasprintf("%s%s", OTR_ERROR_PREFIX, err_msg);
ops->inject_message(opdata, context->accountname,
                    context->protocol, context->username, buf);
free(buf);
```

This is shorter, simpler, and has none of the problems of the original.

[^1]: This is the first time I've seen indentation at 4 columns with tab stops at 8 columns.
[^2]: Not to mention, embedded devices are usually much easier to push into memory pressure.

[libotr]: https://otr.cypherpunks.ca/
[openssl]: /2014/01/16/openssl-rand-api
[master]: https://github.com/off-the-record/libotr/tree/3172d79b3f60513aeb10a22450cb1ca2cf145016
[massage-commit]: https://github.com/ctz/libotr/commit/4c4aac9a4d612f076969b4d6aa69f08ca84ab078
[vector-rewrite]: https://cansecwest.com/slides07/Vector-Rewrite-Attack.pdf
[cwe-14]: http://cwe.mitre.org/data/definitions/14.html

---

# Full comments

### [auth.c][]

```c
77:   auth->our_keyid = 0;
78:   auth->encgx = NULL;
79:   auth->encgx_len = 0;
80:   memset(auth->r, 0, 16);
81:   memset(auth->hashgx, 0, 32);
82:   auth->their_pub = NULL;
83:   auth->their_keyid = 0;
84:   auth->enc_c = NULL;
85:   auth->enc_cp = NULL;
86:   auth->mac_m1 = NULL;
87:   auth->mac_m1p = NULL;
88:   auth->mac_m2 = NULL;
89:   auth->mac_m2p = NULL;
90:   memset(auth->their_fingerprint, 0, 20);
91:   auth->initiated = 0;
92:   auth->protocol_version = 0;
93:   memset(auth->secure_session_id, 0, 20);
94:   auth->secure_session_id_len = 0;
95:   auth->lastauthmsg = NULL;
96:   auth->commit_sent_time = 0;
```

Style: this is pretty much unmaintainable: start with memset, then fill in the exceptions?

Specifically, this pattern goes badly wrong when adding a new struct member without chasing
down all places which initialise one of these types.

```c
1484:     if (auth->encgx) free(auth->encgx);
```

Style: ``if (ptr) free(ptr)`` is just noise.

```c
1485:     auth->encgx = malloc(m_auth->encgx_len);
1486:     memmove(auth->encgx, m_auth->encgx, m_auth->encgx_len);
```

Unchecked malloc.

---

### [b64.c][]

```c
202:   base64len = ((buflen + 2) / 3) * 4;
203:   base64buf = malloc(5 + base64len + 1 + 1);
204:   if (base64buf == NULL) {
205:     return NULL;
206:   }
207:   memmove(base64buf, "?OTR:", 5);
208:   otrl_base64_encode(base64buf+5, buf, buflen);
209:   base64buf[5 + base64len] = '.';
210:   base64buf[5 + base64len + 1] = '\0';
```

This is a highly impractical integer overflow if buflen &ge; ``0xbffffffb`` (for 32-bit ``size_t``),
followed by a heap overflow.  Assert?

Also, there are extant defines with the right semantics for `3` and `4` here.

---

### [context.c][]

```c
129:   context = malloc(sizeof(ConnContext));
130:   assert(context != NULL);
...
139:   smstate = malloc(sizeof(OtrlSMState));
140:   assert(smstate != NULL);
```

Style: Use of `assert(3)` to check malloc success is better than nothing.  But beware `NDEBUG`
removing asserts.

```c
132:   context->username = strdup(user);
133:   context->accountname = strdup(accountname);
134:   context->protocol = strdup(protocol);
```

Three unchecked strdups.  Other users of this structure (`otrl_context_find`, etc.) aren't happy
for these string members to be `NULL`.

---

### [context_priv.h][]

```c
70:   /* generation number: increment every time we go private, and never
71:    * reset to 0 (unless we remove the context entirely) */
72:   unsigned int generation;
```

OK, the comment is accurate.  But this is a library-private struct and nothing reads
this value, ever.

---

### [context_priv.c][]

```c
38:   context_priv->fragment = NULL;
39:   context_priv->fragment_len = 0;
40:   context_priv->fragment_n = 0;
41:   context_priv->fragment_k = 0;
42:   context_priv->numsavedkeys = 0;
43:   context_priv->saved_mac_keys = NULL;
44:   context_priv->generation = 0;
45:   context_priv->lastsent = 0;
46:   context_priv->lastmessage = NULL;
...
```

Like the function in auth.c, this is pretty grot.  `otrl_context_priv_force_finished`
has a clone of this code.

```c
35:   context_priv = malloc(sizeof(*context_priv));
36:   assert(context_priv != NULL);
```

Style: malloc checked with assert.

---

### [dh.c][]

```c
131:   gcry_error_t err = gcry_error(GPG_ERR_NO_ERROR);
...
```

Style: setting the unused error code to 'success' is hazardous if future code does 'goto err' without writing err.

```c
151:   gabdata[1] = (gablen >> 24) & 0xff;
152:   gabdata[2] = (gablen >> 16) & 0xff;
153:   gabdata[3] = (gablen >> 8) & 0xff;
154:   gabdata[4] = gablen & 0xff;
155:   gcry_mpi_print(GCRYMPI_FMT_USG, gabdata+5, gablen, NULL, gab);
156:   gcry_mpi_release(gab);
157: 
158:   hashdata = gcry_malloc_secure(20);
159:   if (!hashdata) {
160:     gcry_free(gabdata);
161:     return gcry_error(GPG_ERR_ENOMEM);
...
269:   sdata[1] = (slen >> 24) & 0xff;
270:   sdata[2] = (slen >> 16) & 0xff;
271:   sdata[3] = (slen >> 8) & 0xff;
272:   sdata[4] = slen & 0xff;
273:   gcry_mpi_print(GCRYMPI_FMT_USG, sdata+5, slen, NULL, s);
274:   gcry_mpi_release(s);
275: 
276:   /* Calculate the session id */
277:   hashdata = gcry_malloc_secure(32);
278:   if (!hashdata) {
279:     gcry_free(sdata);
...
394:   sdata[1] = (slen >> 24) & 0xff;
395:   sdata[2] = (slen >> 16) & 0xff;
396:   sdata[3] = (slen >> 8) & 0xff;
397:   sdata[4] = slen & 0xff;
398:   gcry_mpi_print(GCRYMPI_FMT_USG, sdata+5, slen, NULL, s);
399:   gcry_mpi_release(s);
400: 
401:   /* Calculate the session id */
402:   hashdata = gcry_malloc_secure(20);
403:   if (!hashdata) {
404:     gcry_free(sdata);
```

Style: this encode-and-hash thing keeps happening. Refactor? 

---

### [instag.c][]

```c
36:   if (instag->accountname) free(instag->accountname);
37:   if (instag->protocol) free(instag->protocol);
```

Style: `if (ptr) free(ptr)`.

```c
093:   if (!instf) return gcry_error(GPG_ERR_NO_ERROR);
...
207:   if (!accountname || !protocol) return gcry_error(GPG_ERR_NO_ERROR);
```

It seems strange to report `GPG_ERR_NO_ERROR` here. `GPG_ERR_INV_VALUE` perhaps?

Either that, or mention in the function docs that it will report success and do nothing if called incorrectly.

```c
119:     p->accountname = malloc(pos - prevpos);
120:     memmove(p->accountname, prevpos, pos - prevpos);
...
130:     p->protocol = malloc(pos - prevpos);
131:     memmove(p->protocol, prevpos, pos - prevpos);
...
209:   p = (OtrlInsTag *)malloc(sizeof(OtrlInsTag));
210:   p->accountname = strdup(accountname);
211:   p->protocol = strdup(protocol);
```

Five unchecked malloc/strdups.

---

### [mem.c][]

```c
75: static void otrl_mem_free(void *p)
76: {
77:   void *real_p = (void *)((char *)p - header_size);
78:   size_t n = ((size_t *)real_p)[0];
```

I'm surprised that anything is happy with a `free(3)` replacement which will segfault
on `free(NULL)`.

```c
91:   memset(real_p, 0x00, n);
92: 
93:   free(real_p);
```

General CWE-14 worries about compilers removing memset, based on lack of reads and
subsequent free meaning there cannot be any active aliases in a conforming program.

```c
86:   /* Wipe the memory (in the same way the built-in deallocator in
87:    * libgcrypt would) */
88:   memset(real_p, 0xff, n);
89:   memset(real_p, 0xaa, n);
90:   memset(real_p, 0x55, n);
91:   memset(real_p, 0x00, n);
```

Wut. Doing it four times is just bananas.

Note that libgcrypt says of the repetition: "This does not make much sense: probably this memory
is held in the cache.  We do it anyway."  Also, it doesn't use memset.

I suggest introducing a `void otrl_mem_clear(volatile void *ptr, size_t len)`.

There's more of this on lines 127-130.

---

### [message.c][]

```c
90:       int headerlen = context->protocol_version == 3 ? 37 : 19;
```

This calculation is opaque, and appears elsewhere (proto.c:1018).

```c
104:         *returnFragment = strdup(fragments[0]);
...
116:         *returnFragment = strdup(fragments[fragment_count-1]);
...
132:         *returnFragment = strdup(message);
```

Three unchecked strdups.  Notably, this function's caller returns
`GPG_ERR_ENOMEM` in the same case.  I guess this will cause messages
to go missing under memory pressure.

```c
291:     char *bettermsg = otrl_proto_default_query_msg(accountname, policy);
292:     if (bettermsg) {
293:       *messagep = bettermsg;
294:     }
295:     context->otr_offer = OFFER_SENT;
296:     err = gcry_error(GPG_ERR_NO_ERROR);
```

Error swept under rug if `otrl_proto_default_query_msg` fails (which it does if
malloc fails).

```c
314:       context->context_priv->lastmessage =
315:         gcry_malloc_secure(strlen(original_msg) + 1);
316:       if (context->context_priv->lastmessage) {
317:         char *bettermsg = otrl_proto_default_query_msg(accountname,
318:                           policy);
319:         strcpy(context->context_priv->lastmessage, original_msg);
320:         context->context_priv->lastsent = time(NULL);
321:         otrl_context_update_recent_child(context, 1);
322:         context->context_priv->may_retransmit = 2;
323:         if (bettermsg) {
324:           *messagep = bettermsg;
325:           context->otr_offer = OFFER_SENT;
326:         } else {
327:           err = gcry_error(GPG_ERR_ENOMEM);
328:           goto fragment;
329:         }
330:       }
```

Error swept under rug if `gcry_malloc_secure` fails.  But fortunately not
`otrl_proto_default_query_msg` this time!

```c
751:   combined_buf = malloc(combined_buf_len);
752:   combined_buf[0] = 0x01;
...
```

Unchecked malloc.

```c
780:     size_t qlen = strlen(question);
781:     unsigned char *qsmpmsg = malloc(qlen + 1 + smpmsglen);
782:     if (!qsmpmsg) {
783:       free(smpmsg);
784:       return;
785:     }
786:     strcpy((char *)qsmpmsg, question);
787:     memmove(qsmpmsg + qlen + 1, smpmsg, smpmsglen);
788:     free(smpmsg);
789:     smpmsg = qsmpmsg;
790:     smpmsglen += qlen + 1;
```

Impractical integer underflow followed by heap overflow.
`smpmsglen` is the wrong type for a length, so will be &lt; 0 if very large.
That will make the allocation too small for the subsequent strcpy/memmove.

```c
874:       char *buf = malloc(strlen(OTR_ERROR_PREFIX) + strlen(err_msg) + 1);
875: 
876:       if (buf) {
877:         strcpy(buf, OTR_ERROR_PREFIX);
878:         strcat(buf, err_msg);
879:         ops->inject_message(opdata, context->accountname,
880:                             context->protocol, context->username, buf);
881:         free(buf);
882:       }
883: 
884:       if (ops->otr_error_message_free) {
```

Impractical integer overflow if `strlen(OTR_ERROR_PREFIX) + strlen(err_msg) + 1 > SIZE_MAX`.

```c
922: int otrl_message_receiving(OtrlUserState us, const OtrlMessageAppOps *ops,
...
```

Style: this is a single 951 line function.

```c
1964:     unsigned char *tlvdata = malloc(usedatalen+4);
1965:     char *encmsg = NULL;
1966:     gcry_error_t err;
1967:     OtrlTLV *tlv;
1968: 
1969:     tlvdata[0] = (use >> 24) & 0xff;
1970:     tlvdata[1] = (use >> 16) & 0xff;
1971:     tlvdata[2] = (use >> 8) & 0xff;
1972:     tlvdata[3] = (use) & 0xff;
...
```

Unchecked malloc.

```c
1964:     unsigned char *tlvdata = malloc(usedatalen+4);
1965:     char *encmsg = NULL;
1966:     gcry_error_t err;
1967:     OtrlTLV *tlv;
1968: 
1969:     tlvdata[0] = (use >> 24) & 0xff;
1970:     tlvdata[1] = (use >> 16) & 0xff;
1971:     tlvdata[2] = (use >> 8) & 0xff;
1972:     tlvdata[3] = (use) & 0xff;
1973:     if (usedatalen > 0) {
1974:       memmove(tlvdata+4, usedata, usedatalen);
```

Impratical integer overflow if `usedatalen > SIZE_MAX - 4`.

---

### [privkey.c][]

```c
383:   search->accountname = strdup(accountname);
384:   search->protocol = strdup(protocol);
```

If strdup fails here we continue to insert the new item into the pending list,
which will explode in `pending_find`.

```c
431:   fprintf(privf, "%s", buf);
...
443:   fprintf(privf, " (account\n");
...
457:   fprintf(privf, " )\n");
...
803:       fprintf(storef, "%s\t%s\t%s\t", context->username,
804:               context->accountname, context->protocol);
805:       for(i=0; i<20; ++i) {
806:         fprintf(storef, "%02x", fprint->fingerprint[i]);
807:       }
808:       fprintf(storef, "\t%s\n", fprint->trust ? fprint->trust : "");
```

Unchecked fprintfs, could lead to lost key material if we're (for example) out of disk space.

```c
490:   ppc = malloc(sizeof(*ppc));
491:   ppc->accountname = strdup(accountname);
492:   ppc->protocol = strdup(protocol);
```

Three unchecked mallocs/strdups.

```c
532: #ifndef WIN32
533:   mode_t oldmask;
534: #endif
535: 
536: #ifndef WIN32
537:   oldmask = umask(077);
538: #endif
539:   privf = fopen(filename, "w+b");
540:   if (!privf && errp) {
541:     *errp = gcry_error_from_errno(errno);
542:   }
```

For extra points on Windows here, we could `CreateFile`/`_open_osfhandle`/`_fdopen`
to get similar file permissions behaviour.

---

### [proto.c][]

```c
254:   version_tag = malloc(8);
255:   bufp = version_tag;
```

Unchecked malloc (of a constant size, use stack?)

```c
277:   msg = malloc(strlen(format) + strlen(version_tag) + strlen(ourname) - 3);
```

*Extremely* impractical integer overflow.

```c
466:   bufp = malloc(OTRL_B64_MAX_DECODED_SIZE(12));
467:   bufp_head = bufp;
468:   lenp = otrl_base64_decode(bufp, otrtag+9, 12);
...
```

Unchecked malloc (of a constant size, use stack?) 

---

### [sm.c][]

```c
157:   gcry_mpi_t *msg = malloc(SM_MSG1_LEN * sizeof(gcry_mpi_t));
158:   msg[0] = gcry_mpi_new(SM_MOD_LEN_BITS);
...
175:   gcry_mpi_t *msg = malloc(SM_MSG2_LEN * sizeof(gcry_mpi_t));
176:   msg[0] = gcry_mpi_new(SM_MOD_LEN_BITS);
...
198:   gcry_mpi_t *msg = malloc(SM_MSG3_LEN * sizeof(gcry_mpi_t));
199:   msg[0] = gcry_mpi_new(SM_MOD_LEN_BITS);
...
217:   gcry_mpi_t *msg = malloc(SM_MSG4_LEN * sizeof(gcry_mpi_t));
218:   msg[0] = gcry_mpi_new(SM_MOD_LEN_BITS);
```

Four unchecked mallocs.

```c
295:   input = malloc(totalsize);
296:   input[0] = (unsigned char)version;
...
```

Unchecked malloc.

```c
342:   *buffer = malloc(*buflen * sizeof(char));
343: 
344:   bufp = *buffer;
345:   lenp = totalsize;
346: 
347:   write_int(count);
...
```

Unchecked malloc.

```c
383:   *mpis = malloc(thecount * sizeof(gcry_mpi_t));
384: 
385:   for (i=0; i<thecount; i++) {
386:     (*mpis)[i] = NULL;
387:   }
```

Unchecked malloc.

---

### [tlv.c][]

```c
31:   OtrlTLV *tlv = malloc(sizeof(OtrlTLV));
32:   assert(tlv != NULL);
...
35:   tlv->data = malloc(len + 1);
36:   assert(tlv->data != NULL);
```

Style: mallocs checked with assert.

---

### [userstate.c][]

```c
52:   otrl_context_forget_all(us);
53:   otrl_privkey_forget_all(us);
54:   otrl_privkey_pending_forget_all(us);
55:   otrl_instag_forget_all(us);
56:   free(us);
57: }
```

`otrl_userstate_free` is allergic to `NULL` userstate via `otrl_context_forget_all`,
which is a shame because that's `otrl_userstate_create`'s error handling mechanism.

This is made worse by hiding the fact that this is a pointer type behind a typedef,
and not documentating that it can be `NULL`, and not doing any checks in the
tests/example code (which invariably get copied into application code).

It's unlikely to be a problem here because `otrl_userstate_create` tends to get called
once, early on, and isn't generally going to encounter an allocation failure. 

[auth.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/auth.c
[b64.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/b64.c
[context.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/context.c
[context_priv.h]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/context_priv.h
[context_priv.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/context_priv.c
[dh.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/dh.c
[instag.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/instag.c
[mem.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/mem.c
[message.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/message.c
[privkey.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/privkey.c
[proto.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/proto.c
[sm.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/sm.c
[tlv.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/tlv.c
[userstate.c]: https://github.com/ctz/libotr/blob/4c4aac9a4d612f076969b4d6aa69f08ca84ab078/src/userstate.c
