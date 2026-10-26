# Synthetic Muse — Video Pilot 0.1

## Σκοπός
Πρώτο **πραγματικό** image-to-video MP4 σε SaladCloud. Χρησιμοποιεί Stable Video Diffusion 14 καρέ, **όχι Kandinsky**. Δεν δέχεται κείμενο-prompt: δέχεται φωτογραφία + κίνηση. Μόνο μη ρητό δοκιμαστικό υλικό, με εφαρμογή της άδειας/πολιτικής Stability AI.

## Πριν πληρώσεις GPU
- Το smoke test 0.4 έχει ήδη επιβεβαιώσει CUDA GPU. Άφησέ το STOPPED.
- Περιμένουμε **πράσινο** GitHub build για το video pilot. Αν το build αποτύχει, ΜΗΝ προχωρήσεις σε Salad.
- Το νέο image είναι `ghcr.io/labanter13/synthetic-muse-video-pilot:0.1`. Αν είναι Private, χρειάζεται public visibility ή private registry credentials. Μην ανεβάσεις κωδικούς στο chat.
- Η ενεργοποίηση GPU αρχίζει να χρεώνει· μόλις έχεις το MP4, κατέβασέ το και πάτησε Stop.
- Σχεδιαστική αρχική εκτίμηση: **RTX 3060 12GB, 4 vCPU, 16GB RAM, 25GB extra disk, 1 replica**. Πρόκειται για μη δοκιμασμένη πραγματική διαμόρφωση, όχι βεβαιωμένη συμβατότητα. Για την πρώτη εκτέλεση ενδέχεται να χρειαστεί περισσότερη RAM ή χρόνος λήψης μοντέλου.
- Ορισμός **PILOT_API_KEY** ως secret environment variable στη Salad με τιμή τουλάχιστον 24 χαρακτήρες. Δημιούργησέ το τοπικά με `openssl rand -hex 24`. Μη στείλεις το secret εδώ.
- Ενεργοποίησε το Container Gateway σε HTTP **port 8000** και έλεγξε TLS HTTPS. Η εφαρμογή ακούει σε IPv6 (::).
- Το model download γίνεται **στην πρώτη εργασία** (όχι στο build). Θα απαιτηθούν αρκετά GB και παραπάνω χρόνος. Πρόσεχε το διαθέσιμο credit.
- Από το HTTPS gateway: βάλε το private key, ανέβασε reference JPG/PNG, επίλεξε Steps=16 Motion=90, πάτα Generate. Όταν εμφανιστεί Completed πάτα Download MP4 **πριν** Stop.
- Αν εμφανιστεί `failed`, κράτησε τα logs, πάτα Stop και μην κάνεις συνεχείς επανεκκινήσεις.

## Περιορισμοί / προειδοποιήσεις
- Δεν κατασκευάστηκε ούτε δοκιμάστηκε πραγματικό MP4 ακόμη· μόνο ο κώδικας/CI build.
- Portrait εικόνα μεταφέρεται σε landscape κάδρο 1024×576 με blurred sidebars για να μην κοπεί το πρόσωπο. Το αποτέλεσμα θα είναι διαφορετικό από το portrait Kandinsky video.
- 14 frames × 7 fps ~2 sec, χωρίς ήχο· ποιότητα άγνωστη.
- Βάρη SVD και downloads από Hugging Face είναι εξωτερικά και υπό τους όρους του μοντέλου. Δεν ενσωματώνουμε βάρη στο GHCR image.
- Αποθήκευση προσωρινή. Με reallocation μπορεί να χαθούν weights και MP4. **Πάντα κατέβασε το MP4 πριν Stop**.
- Μην ενεργοποιήσεις Auto Recharge. Κράτησε μικρό budget. Ο χρόνος GPU, RAM, download, retries κοστίζουν.
- Αυτό το pilot **δεν** είναι κατάλληλο για adult content και δεν αποτελεί το production Kandinsky deployment.
