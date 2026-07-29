N2N Federation Capture Analysis bundle — 2026-07-18
CML lab-health chat exchange over secured channels (specs 060/063, H14)
Produced by Nick's claw (as65007-7.7.7.7)

Contents
--------
N2N-CML-Health-Capture-Analysis-20260718.pdf   The report (start here). 6 pages,
                                               every claim backed by verbatim tool output.
N2N-CML-Health-Capture-Analysis-20260718.html  Same report, HTML source.
n2n-cml-health-20260718.pcap                   The packet capture. 2,952 packets,
                                               13:34:01–14:14:42 EDT, BPF
                                               "tcp port 20203 or XXXXX or XXXXX".
chat-transcript-5f1af883.txt                   Local transcript of the chat session —
                                               the cleartext of the 494-byte encrypted
                                               record at frame 34.
bgp-daemon-log-capture-window.log              Daemon log trimmed to the capture window
                                               (13:34:03–14:15:20). Note the ERROR line at
                                               13:34:20,600 — it matches frame 36's arrival
                                               to the millisecond (John's side error
                                               transported over the encrypted channel).
SHA256SUMS                                     Integrity manifest for every file above.
                                               Verify with:  sha256sum -c SHA256SUMS

Quick verification of the headline claims
-----------------------------------------
tshark -r n2n-cml-health-20260718.pcap -q -z io,phs          # 2952 frames, 982 TLS
tshark -r n2n-cml-health-20260718.pcap -q -z conv,tcp        # the 4 conversations
tshark -r n2n-cml-health-20260718.pcap -Y tls.app_data | wc -l   # 982
strings n2n-cml-health-20260718.pcap | grep -ciE 'CML|health check|Nick'   # 0 — payloads dark

Series: analysis-20260714 (cleartext era) · analysis-20260717 (first encrypted
capture) · analysis-20260718 (this bundle).

Redaction note (2026-07-22)
---------------------------
Before publication, live ngrok tunnel ports were replaced with "XXXXX" in every
file of this bundle, including inside the pcap (same-length byte substitution in
the pcapng capture-filter metadata; packet payloads are TLS and were untouched).
Stale tunnel ports from rotated sessions (e.g. 20203) are left as captured.
SHA256SUMS was regenerated after redaction.
