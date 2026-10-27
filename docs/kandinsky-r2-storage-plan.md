# Synthetic Muse — μόνιμο cache για Kandinsky 6.0

## Πρόβλημα που επιβεβαιώθηκε στις 27 Οκτωβρίου 2026
- GPU instance της SaladCloud κατέβαζε μοντέλο μέσω Hugging Face.
- Στα logs: KANDINSKY_DOWNLOAD_PROGRESS elapsed_sec=60 cache_mb=5614.5, 15/25 αρχεία.
- Στη συνέχεια System Event: Instance Interrupted (Node Offline).
- Το νέο instance δεν κληρονομεί τον δίσκο του προηγούμενου. Η λήψη χάνεται.
- Το HF_HOME στην GPU είναι προσωρινό και ΔΕΝ αρκεί από μόνο του για μόνιμο cache.

## Επιλογή αποθήκευσης
Cloudflare R2 **Standard** με ιδιωτικό bucket:
  synthetic-muse-model-cache

Τιμές που ελέγχθηκαν στις 27 Οκτωβρίου 2026:
- 10 GB-month / μήνα δωρεάν στη Standard κλάση.
- $0.015 ανά επιπλέον GB-month.
- Δωρεάν outbound transfer απευθείας από R2 (χωρίς χρεώσεις egress της R2).
- ~26.7 GB μοντέλο => ενδεικτικά ~$0.25/μήνα πάνω από τη δωρεάν ποσότητα, εφόσον η δωρεάν ποσότητα δεν καταναλώνεται από άλλα δεδομένα. Ζήτηση για R2 subscription/billing. Άλλες λειτουργίες ή υπηρεσίες μπορούν να προσθέσουν κόστος.
- Ο λογαριασμός Cloudflare και το bucket δημιουργούνται από τον χρήστη. Ο χρήστης δεν στέλνει ποτέ tokens στον βοηθό.

Πηγές: https://developers.cloudflare.com/r2/pricing/ και https://developers.cloudflare.com/r2/get-started/s3/

## Αρχιτεκτονική (υπό κατασκευή — δεν λειτουργεί ακόμα)
1. Δημιουργία ιδιωτικού R2 bucket (Standard).
2. Token Object Read & Write περιορισμένο ΜΟΝΟ σε αυτό το bucket.
3. Εγγραφή των R2 credentials στα SaladCloud Environment Variables (secrets), όχι στον κώδικα/GitHub.
4. Αρχική «σπορά» των βαρών: download από Hugging Face, upload στο R2. Να γίνεται χωρίς πληρωμένη GPU όταν γίνεται (π.χ. ξεχωριστό CPU seed task με επαρκή προσωρινό δίσκο). Κάθε upload να επαληθεύεται.
5. Σε κάθε νέο GPU instance, download από R2 στον τοπικό προσωρινό δίσκο και loading των τοπικών αρχείων.
6. Προτεραιότητα στα checksums, fail-closed manifest και επανάληψη μόνο ελλιπών αρχείων. Η ύπαρξη αντικειμένου ΔΕΝ αρκεί: έλεγχος μεγέθους/hash.
7. Μελλοντικά, outputs MP4 να ανεβαίνουν επίσης στο R2 πριν σταλεί completed (ιδιωτικός διαφορετικός prefix ή bucket).
8. Μία εργασία ανά replica. Ανακτήσιμο job state με durable queue θα χρειαστεί για production.

### Τι ΔΕΝ λύνει το R2
- Τα νέα Salad nodes εξακολουθούν να χρειάζεται να κατεβάσουν τα βάρη στο δικό τους δίσκο πριν από το inference. Το R2 προστατεύει από την επανάληψη λήψης από Hugging Face, δεν προσφέρει μόνιμο τοπικό disk/VRAM.
- Αν το πρώτο HF download διακοπεί προτού ανέβουν τα βάρη στο R2, δεν έχουμε ακόμη durable αντίγραφο. Η αρχική μεταφορά είναι ξεχωριστή ενέργεια.
- Η R2 ταχύτητα μεταφοράς εξαρτάται από το δίκτυο του node.
- Αν η δημιουργία model snapshots απαιτεί πολλαπλές εγγραφές, να αποφεύγεται η δημοσίευση μισοτελειωμένου manifest.
- Πριν από οποιαδήποτε εμπορική / ευαίσθητη χρήση ελέγχονται ξεχωριστά όροι και κανονισμοί μοντέλου, υπηρεσίας και storage provider.

## Ονόματα config που προτείνουμε για την υλοποίηση
R2_ENDPOINT = https://<account-id>.r2.cloudflarestorage.com
R2_BUCKET = synthetic-muse-model-cache
R2_ACCESS_KEY_ID = private access key (secret)
R2_SECRET_ACCESS_KEY = private secret access key (secret)
R2_PREFIX = model-cache/kandinsky-6-lite-distill/

## Επόμενο πραγματικό βήμα
Ο χρήστης δημιουργεί **ιδιωτικό R2 Standard bucket**, χωρίς να δημιουργήσει ακόμη API token. Μετά γράφουμε και ελέγχουμε εκτός GPU τον κώδικα backup/restore και την πρώτη σπορά, πριν τον επόμενο πληρωμένο GPU έλεγχο.
