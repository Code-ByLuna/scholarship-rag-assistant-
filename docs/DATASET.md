# Dataset integrity and provenance

The supplied scholarship data files are preserved. scholarship_dataset_ready.json is authoritative:
16 unique records; the metadata reports 18 initial source records and two exact
duplicates removed. The supplied combined_scholarship_schemes_cleaned.json also
contains 16 preserved records after deduplication. Original keys remain noncontiguous.

The loader validates counts, unique IDs, mandatory provenance and equality of every
original_record to its source-corpus counterpart. Ready JSONL is a supplied
id/text/metadata projection for retrieval, not a second authoritative record schema.
The application creates section chunks from the ready JSON to retain precise sources.
No semantic scholarships are merged and no source facts are added.

Known source issues: ST pre-matric income differs between Details and Eligibility;
the correct current income threshold requires official verification. Both disability schemes describe offline
implementation while specifying online application. These notes are preserved and
retrieved with the relevant sections and explained naturally in generated answers.

Many records lack source URLs/names. Empty URLs become null; the UI explicitly says
"Source information unavailable in dataset". No URLs are synthesized.
The corpus is a supplied snapshot. The application cannot verify live availability,
deadlines or current scholarship amounts without an updated authoritative source.
