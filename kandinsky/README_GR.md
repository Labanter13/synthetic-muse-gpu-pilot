# Synthetic Muse — Kandinsky 6 Lite Distill Pilot

Πειραματικό image-to-video της Emma με περιγραφή κίνησης σε prompt.

## Πραγματικές δυνατότητες
- Επίσημο μοντέλο `kandinskylab/Kandinsky-6.0-Lite-distill-5s-Diffusers`; 26.7 GB checkpoint, άδεια MIT.
- Diffusers `Kandinsky6TI2VAPipeline`; 121 frames × 24 fps, portrait 480x864, no audio, 10 diffusion steps, guidance=1.
- Το `enable_model_cpu_offload()` και `vae.enable_tiling()` περιορίζουν τη χρήση VRAM.
- Η GPU RTX 4090 24 GB έχει benchmark στην επίσημη native pipeline, όχι εγγύηση ίδιων επιδόσεων στη συγκεκριμένη υλοποίηση Diffusers.
- Πρώτη φόρτωση απαιτεί λήψη δεκάδων GB. Ο server είναι επιτρεπτό να αργήσει. Η αποθήκευση είναι προσωρινή στη SaladCloud.
- Δεν έχουμε τρέξει inference ακόμη. Το CI ελέγχει την κατασκευή Docker και τις Python imports, όχι τη GPU.
- Μην χρησιμοποιήσεις το αποτέλεσμα χωρίς έλεγχο δικαιωμάτων εικόνας, ταυτότητας και πολιτικών δημοσίευσης.
- Μην εμφανίζεις `PILOT_API_KEY` σε screenshot ή στο GitHub.

## Διαμόρφωση
Προτεινόμενο για δοκιμή: RTX 4090 (24 GB), 8 vCPU, **τουλάχιστον 48 GB RAM, προτιμότερα 64 GB**, 75 GB extra disk, 1 replica, Low Priority εφόσον διαθέσιμο.
HTTP Container Gateway 8000. Environment variable `PILOT_API_KEY` με τυχαίο secret >=24 χαρακτήρες.
Startup, readiness, liveness probes απενεργοποιημένα στο αρχικό pilot. Autostart OFF.
Το εκτιμώμενο κόστος ελέγχεται στο Salad UI ΠΡΙΝ την εκκίνηση.

## Πρώτη δοκιμή
- Ενεργοποίηση container μόνο μετά από πράσινο CI και επιβεβαίωση public GHCR.
- `/health` : `cuda:true`, `configured:true`.
- Παρέχουμε reference εικόνα της Emma και prompt σε website.
- Παρακολουθούμε `KANDINSKY_STAGE` στα Container Logs.
- Κατεβάζουμε MP4 προτού σταματήσουμε το instance. Σε σφάλμα Stop αμέσως, καταγραφή logs και διάγνωση πριν νέα χρέωση.

## Περιορισμοί
1. Δεν εγγυόμαστε ποιότητα, ταχύτητα ή ταυτότητα χαρακτήρα πριν την πρώτη παραγωγή.
2. Το πρώτο inference μπορεί να αποτύχει από RAM, VRAM, disk, dependency ή CUDA incompatibility. Το καταγράφουμε με σαφές error.
3. Εκτός παραγωγής, δεν υπάρχει persistent storage / επανάληψη εργασιών / αυτοματοποιημένα πολλαπλά clips.
4. Δοκιμαστικό χωρίς ρητό περιεχόμενο.
