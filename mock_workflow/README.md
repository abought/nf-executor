Mock workflow. Used to verify logging features.

## Running the workflow
**Note**: This string is an example. To use within the django app, launch from within django (the URL must be authenticated to receive reports). The below example uses netcat instead, for decoupled debugging.

In one window, create a server that dumps output to console (and also to a file):
```bash
python dump_requests.py -a localhost -p 8888 | tee payloads.txt
```

In another run the workflow
```bash
JOB_ID="job-`date "+%F-%H-%M-%S"`"
nextflow run hello.nf -name $JOB_ID -with-weblog "http://localhost:8888" -with-report "report-$JOB_ID.html" -with-trace

nextflow log $JOB_ID
nextflow clean -f
```

If you prefer, the captured output across requests (JSONL format) can optionally be converted into a regular JSON document: `jq -s '.' content.txt > payloads.txt`
