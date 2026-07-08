# RDLLM Dijelaskan

## ELI5

Bayangkan jawaban AI seperti laporan sekolah. RDLLM membuat AI menunjukkan
sumber yang dipakai, kalimat mana didukung sumber mana, dan siapa yang harus
mendapat kredit atau pembayaran.

## Simple

RDLLM menambahkan source footer yang terlihat pada jawaban AI. RDLLM memeriksa
apakah sumber mendukung claims dan menghubungkan penggunaan sumber ke payout
atau escrow.

## Non-Technical

User melihat sources dan Claim Evidence. Creator mendapat bukti atribusi.
Operator mendapat gate sebelum menampilkan jawaban sebagai grounded atau
royalty-bearing.

## Technical

RDLLM membuat source rows dan Claim Evidence rows berisi claim hash, support
score, evidence span hash, warrant status, source-disagreement status, dan payout
allocation. Verifier menghitung ulang hashes, citations, links, metrics,
attribution-gap closure, dan `source_grounding_acceptance`.

