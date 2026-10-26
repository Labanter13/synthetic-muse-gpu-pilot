# Synthetic Muse — Δοκιμή GPU V0.2

## Γιατί αυτό το πακέτο;

Ο στόχος είναι η παραγωγή image-to-video της Emma μέσω SaladCloud. **Δεν έχουμε ακόμα κατασκευάσει ή εκτελέσει πραγματικό Kandinsky Docker image σε GPU.** Για να αποφύγουμε άσκοπες χρεώσεις, υπάρχουν δύο στάδια:

1. **GPU smoke test:** ένα μικρό, ακίνδυνο container ελέγχει ότι το GitHub image τραβιέται από το SaladCloud και βλέπει NVIDIA GPU. Δεν παράγει video.
2. **Kandinsky prototype:** το υπάρχον πειραματικό Docker/API για video. Δεν πρέπει να γίνει paid deploy πριν διορθωθεί και επαληθευτεί πλήρως, επειδή η πρώτη εκκίνηση εγκαθιστά πακέτα, μεταφέρει πολλά GB και μπορεί να αποτύχει ή να είναι ακριβή.

## Α. Ενέργειες στο GitHub — χωρίς να αγοράσουμε GPU

1. Δημιούργησε **private, empty** repository `synthetic-muse-gpu-pilot` στον λογαριασμό GitHub. Μη βάλεις "Add a README".
2. Κατέβασε/αποσυμπίεσε το ZIP. Στο Mac, άνοιξε Terminal και μπες στον αποσυμπιεσμένο φάκελο που περιέχει το `README_GR.md`.
3. Εκτέλεσε `git init && git add . && git commit -m "Initial GPU pilot" && git branch -M main`.
4. Εκτέλεσε `git remote add origin https://github.com/USERNAME/synthetic-muse-gpu-pilot.git` (βάλε το πραγματικό username σου).
5. Εκτέλεσε `git push -u origin main`. Αν σου ζητηθεί authentication, χρησιμοποίησε την επίσημη ροή GitHub· **μη στείλεις κωδικούς/token στο chat**.
6. Στο GitHub → Actions → `Build GPU smoke container` δες αν ολοκληρώνεται επιτυχώς. Τα repositories έχουν μεταβλητά όρια δωρεάν GitHub Actions minutes.
7. Το αναμενόμενο image tag θα είναι `ghcr.io/USERNAME/synthetic-muse-gpu-smoke:0.2` (όπου USERNAME ο owner του GitHub repo).

**Εάν ο GHCR package είναι private**, η SaladCloud χρειάζεται read access από GitHub registry credential, συνήθως token με `read:packages`. Ποτέ μην μοιραστείς το token μαζί μου. Μην το τοποθετήσεις στον κώδικα.

## Β. Πριν πατήσουμε Deploy στη SaladCloud

- Ελέγχουμε ότι GitHub Actions → build πράσινο, ότι υπάρχει image tag, ότι το Salad Portal προσφέρει GPU RTX 4090/24GB ή ανάλογη, κατάλληλο system RAM/δίσκο, και πώς γίνεται ανάγνωση private GHCR.
- Η SaladCloud έχει προπληρωμένη χρέωση, περιλαμβανομένου του χρόνου εκκίνησης και του χρόνου που ο container παραμένει running. Η τρέχουσα ελάχιστη φόρτιση στον λογαριασμό εμφανίστηκε $5· δεν χρειάζεται φόρτιση για το βήμα Α.
- Πριν ενεργοποιήσεις οποιοδήποτε container, ελέγχουμε τα επίπεδα χρέωσης, και κρατάμε το auto-recharge κλειστό.
- Ο GPU smoke worker επιστρέφει `GET /health` JSON με `gpu_visible` για διαγνωστικό έλεγχο. Δεν χρειάζεται να αφήσουμε κάποιο endpoint ανοικτό δημόσια.
- Για την πληρωμένη δοκιμή ορίζουμε 1 instance και σταματάμε/κλιμακώνουμε σε 0 μόλις ολοκληρωθεί το smoke test, παρακολουθώντας το billing.

## Γ. Μόνο μετά το successful smoke

- Ολοκληρώνουμε/διορθώνουμε το Kandinsky installer και φτιάχνουμε **δεύτερο** Docker image.
- Δοκιμάζουμε το image-to-video από φωτογραφία της Emma, με ρητά μη πορνογραφικό prompt.
- Μετράμε πλήρη χρόνο (download, compile, load, generate, export), κόστος GPU, επιτυχία/αποτυχία, ποιότητα, και από εκεί αποφασίζουμε αν προχωράμε.

## Τι έχουμε και τι όχι

**Έτοιμα / ελεγχόμενα στατικά:** GPU smoke Dockerfile, GPU detection endpoint, GitHub Actions workflow για Linux AMD64 image, βασικός έλεγχος Python.

**Δεν έχουν ελεγχθεί:** πραγματικό Docker build στο GitHub, GHCR login, Salad GPU execution, Kandinsky model execution, private ingress, πραγματικό image-to-video. Δεν έχει γίνει καμία χρέωση από αυτό το αρχείο.

## Χρήσιμη τεκμηρίωση

- https://docs.salad.com/container-engine/how-to-guides/registries/github-ghcr
- https://docs.salad.com/container-engine/explanation/billing-pricing/billing
- https://github.com/kandinskylab/kandinsky-6
