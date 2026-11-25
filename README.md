NPC Decision-Making untuk Survival Game

Nama: Daren Henokh Tololiu NIM: 20240801111 Mata kuliah: Game Development

Proyek ini mengembangkan "otak" NPC pada sebuah Survival Game. NPC harus bisa bertahan hidup, menghadapi musuh, mengelola sumber daya (peluru, medkit, makanan, stamina), dan menyesuaikan perilakunya ketika kondisi permainan berubah.

Empat pendekatan decision-making diimplementasikan dari nol dengan Python, tanpa library khusus decision-making. Hanya library standar yang dipakai (math, random, dataclasses, enum, typing).

Decision Tree
Behaviour Tree
Fuzzy Logic
Markov Systems

Ditambah satu NPC Hybrid yang menggabungkan keempatnya.

1. Cara kerja secara umum

Semua algoritma memakai pola yang sama:

Kondisi game (GameState)  ->  Algoritma decision-making  ->  Aksi (Action)

GameState adalah informasi yang diamati NPC: HP, rasa lapar, stamina, peluru di magazen, peluru cadangan, medkit, makanan, jarak musuh terdekat, jumlah musuh, dan ada tidaknya cover.

Action adalah pilihan NPC: ATTACK, HEAL, RETREAT, TAKE_COVER, RELOAD, EAT, SCAVENGE, REST, PATROL.

Secara formal, algoritma adalah fungsi f : S -> A yang memetakan state s ke aksi a. Setiap kelas NPC punya method decide(state) yang mengembalikan Decision. Simulasi memanggilnya berulang pada setiap tick:

python
s = world.observe()      # NPC mengamati kondisi
dec = npc.decide(s)      # algoritma memutuskan
world.step(dec)          # dunia menjalankan aksi, musuh bergerak, rasa lapar naik

2. Penjelasan tiap algoritma
2.1 Decision Tree (survival_npc/decision_tree.py)

NPC menjawab pertanyaan ya/tidak secara berurutan sampai tiba pada aksi.

Komponen	Fungsi	Di kode
Decision node	Mengevaluasi satu kondisi C_n(s) bernilai 0 atau 1	DecisionNode
Branch	Jalur True atau False	true_node, false_node
Action node	Aksi akhir	ActionNode

Evaluasi dilakukan secara rekursif:

D(n, s) = a_n                 jika n adalah action node
        = D(n_true,  s)       jika C_n(s) = 1
        = D(n_false, s)       jika C_n(s) = 0

Rumus ini diimplementasikan langsung di fungsi evaluate_tree().

Contoh (pohon dari materi kuliah): HP 80, jarak musuh 5, peluru 10. HP < 30? salah, Distance < 10? benar, Ammo > 0? benar, maka hasilnya ATTACK.

Pohon survival lengkap (build_survival_tree) menambahkan keputusan untuk lapar, medkit, cover, peluru cadangan, dan gerombolan musuh.

Kelebihan: sederhana, cepat, mudah dibaca dan di-debug (jalur keputusan bisa dicetak).
Kekurangan: tidak mengenal aksi yang butuh beberapa tick, dan pohon membesar bila perilaku bertambah.

2.2 Behaviour Tree (survival_npc/behaviour_tree.py)

Perilaku disusun sebagai pohon task yang dijalankan tiap tick. Setiap node mengembalikan salah satu status: SUCCESS, FAILURE, atau RUNNING.

Node	Perilaku
Selector	Mencoba anak dari kiri ke kanan, berhenti saat ada yang SUCCESS atau RUNNING (seperti OR)
Sequence	Menjalankan anak dari kiri ke kanan, berhenti saat ada yang FAILURE atau RUNNING (seperti AND)
Condition	Mengecek kondisi, hasilnya SUCCESS atau FAILURE
Task	Aksi instan, langsung SUCCESS
TimedTask	Aksi berdurasi (RELOAD, HEAL selama 2 tick), RUNNING sampai selesai

Struktur pohon survival:

ROOT (Selector)
├── Hadapi Ancaman (Sequence: ada musuh?)
│   └── Selector: darurat -> heal -> reload -> bertarung -> berlindung -> mundur
├── Kelola Sumber Daya (Selector: lapar -> obati -> isi ulang -> istirahat -> cari bekal)
└── Patroli

Urutan anak menunjukkan prioritas. Bila aksi berdurasi diinterupsi cabang yang lebih penting, progresnya diulang dari nol.

Kelebihan: mengendalikan urutan dan status eksekusi, mudah menambah perilaku (tambah subtree).
Kekurangan: aksi berdurasi bisa terinterupsi musuh sehingga NPC lebih rentan (terlihat di benchmark).

2.3 Fuzzy Logic (survival_npc/fuzzy_logic.py)

Kondisi tidak hanya benar atau salah, tetapi punya derajat keanggotaan antara 0 dan 1. Contoh: HP 35 termasuk Low dengan derajat 0,5 sekaligus Medium dengan derajat 0,5.

Fungsi keanggotaan HP (h dalam [0, 100]):

Low(h)    = 1 jika h <= 20;  (50-h)/30 jika 20 < h < 50;  0 jika h >= 50
Medium(h) = 0 jika h <= 20;  (h-20)/30 jika 20 < h <= 50; (80-h)/30 jika 50 < h < 80;  0 jika h >= 80
High(h)   = 0 jika h <= 50;  (h-50)/30 jika 50 < h < 80;  1 jika h >= 80
Near(d)   = clip((10 - d) / 8, 0, 1)

Langkah keputusan:

Hitung derajat keanggotaan semua kondisi.
Kekuatan rule = bobot x min dari semua kondisi di rule (operator AND).
Skor sebuah aksi = max dari kekuatan semua rule yang menghasilkan aksi itu (operator OR).
Pilih aksi dengan skor tertinggi. Bila seri, gunakan daftar prioritas (PRIORITY) yang mendahulukan keselamatan.

Contoh (HP 35, jarak 4 m): Low=0,5, Medium=0,5, High=0, Near=0,75. Skor RETREAT = min(0,5; 0,75) = 0,5, TAKE_COVER = 0,5, ATTACK = 0. Terjadi seri, dan prioritas memilih RETREAT.

Rule dari materi kuliah ada di slide_rules(). Rule lengkap untuk survival ada di survival_rules() (14 rule, termasuk amunisi, medkit, lapar, stamina, dan jumlah musuh).

Kelebihan: keputusan halus tanpa perubahan mendadak di ambang batas.
Kekurangan: banyak parameter (bentuk fungsi dan bobot) yang harus di-tuning.

2.4 Markov Systems (survival_npc/markov.py)

Perilaku berikutnya dipilih secara probabilistik, bergantung pada state saat ini (Markov property): P(X_{t+1} | X_t, ..., X_0) = P(X_{t+1} | X_t).

Matriks transisi dari materi kuliah, dengan state [Patrol, Attack, Retreat]:

        Patrol  Attack  Retreat
Patrol  [0.60    0.35    0.05]
Attack  [0.20    0.70    0.10]
Retreat [0.50    0.10    0.40]

Setiap baris berjumlah 1. Distribusi setelah n langkah dihitung dengan pi(t+1) = pi(t) . P. Mulai dari Patrol: pi1 = [0,60; 0,35; 0,05] dan pi2 = [0,455; 0,460; 0,085].

Adaptasi terhadap kondisi game: sebelum mengundi, probabilitas pada baris state saat ini dikalikan faktor konteks lalu dinormalisasi ulang agar tetap berjumlah 1. Contoh: HP rendah menaikkan peluang Retreat, peluru habis menurunkan peluang Attack, tidak ada musuh membuat Attack mustahil. Mode terpilih lalu diterjemahkan menjadi aksi konkret.

Kelebihan: perilaku bervariasi dan tidak mudah ditebak pemain.
Kekurangan: hasilnya acak sehingga bisa memilih aksi yang kurang aman bila dipakai sendirian.

2.5 Hybrid (survival_npc/hybrid.py)

Behaviour Tree dipakai sebagai pengatur utama yang memanggil algoritma lain sesuai situasi:

Prioritas	Situasi	Algoritma
1	HP < 30 dan musuh dekat (darurat)	Decision Tree
2	Ada musuh	Fuzzy Logic
3	Butuh makan, heal, atau reload	Decision Tree
4	Situasi aman	Markov (patroli, cari bekal, istirahat secara bervariasi)

3. Dunia simulasi (survival_npc/world.py)

Simulasi sederhana untuk menguji NPC: musuh muncul acak dan mendekat, bisa menyerang jarak dekat dan jarak jauh, cover mengurangi kerusakan, peluru dan makanan terbatas, rasa lapar naik tiap tick, dan loot bisa ditemukan lewat SCAVENGE. NPC mati bila HP mencapai 0.

4. Cara menjalankan

Butuh Python 3.8 atau lebih baru. Tidak perlu pip install.

bash
python main.py

Keluaran program:

Verifikasi terhadap contoh hitungan materi kuliah (Decision Tree, Fuzzy, Markov, Behaviour Tree).
Tabel keputusan tiap algoritma pada skenario yang sama.
Jejak simulasi HybridNPC selama 30 tick.
Benchmark 60 episode x 300 tick untuk setiap algoritma.

Contoh memakai salah satu NPC dari kode sendiri:

python
from survival_npc.common import GameState
from survival_npc.fuzzy_logic import FuzzyNPC

npc = FuzzyNPC()
s = GameState(hp=35, enemy_distance=4, enemy_count=1)
print(npc.decide(s))

5. Hasil benchmark (seed 0-59, 300 tick)
Algoritma	Bertahan hidup	Kill rata-rata
Decision Tree	92%	25,2
Behaviour Tree	52%	21,6
Fuzzy Logic	82%	23,1
Markov System	70%	20,1
Hybrid	85%	24,9

Angka bergantung pada parameter dunia simulasi di world.py, jadi hanya berlaku sebagai perbandingan relatif.

Analisis singkat

Decision Tree unggul di simulasi ini karena semua aksinya instan dan bereaksi langsung.
Behaviour Tree paling rendah karena RELOAD dan HEAL butuh 2 tick dan dapat terinterupsi musuh.
Fuzzy Logic stabil karena keputusannya berubah halus mengikuti kondisi.
Markov sendirian kurang aman karena memilih secara acak; cocok untuk variasi saat situasi aman.
Hybrid menggabungkan kelebihan keempatnya: refleks cepat saat darurat, taktik halus saat tempur, dan variasi saat aman.
