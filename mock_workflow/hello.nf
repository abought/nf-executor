#!/usr/bin/env nextflow

params.greeting = 'Hello world!'

greeting_ch = Channel.of(params.greeting)

process SPLITLETTERS {
    input:
    val x

    output:
    path 'chunk_*'

    script:

    """
    printf '$x' | split -b 6 - chunk_
    """
}

process CONVERTTOUPPER {
    // Can use this to test retry logic,
    errorStrategy 'retry'
    maxErrors 10

    input:
    path y

    output:
    stdout

    script:
    // Can add "(exit 1) to this script when we need to capture examples of abort/retry/error logic
    // Or for retries that eventually succeed...
    //     (( RANDOM%2 == 0 )) && (exit 0) || (exit 1)
    """
    (( RANDOM%2 == 0 )) && (exit 0) || (exit 1)
    cat $y | tr '[a-z]' '[A-Z]'
    """
}

workflow {
    letters_ch = SPLITLETTERS(greeting_ch)

    results_ch = CONVERTTOUPPER(letters_ch.flatten())

    results_ch.view { val -> val }
}
