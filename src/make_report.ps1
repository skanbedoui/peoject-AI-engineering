$root = Split-Path -Parent $PSScriptRoot
$output = Join-Path $root 'report.pdf'

function Escape-PdfText([string]$text) {
    return $text.Replace('\', '\\').Replace('(', '\(').Replace(')', '\)')
}

function Page-Stream([string[]]$lines) {
    $stream = "BT`n/F1 11 Tf`n50 750 Td`n"
    foreach ($line in $lines) {
        $stream += "($(Escape-PdfText $line)) Tj`n0 -16 Td`n"
    }
    return $stream + "ET`n"
}

$page1 = Page-Stream @(
    'Project 0 - Legal Clause Classification',
    'Local Ollama baseline | 13 September 2026',
    '',
    'Task and data',
    'Binary classification: does a contract clause contain the named legal category?',
    'The supplied category_descriptions.csv defines categories but has no clauses or labels.',
    'This run uses 50 synthetic clauses derived from those definitions, balanced Yes/No.',
    'Example: Audit Rights - Customer may audit Supplier records - expected Yes.',
    '',
    'Setup',
    'Model: Ollama llama3.1:latest, 8.0B parameters, Q4_K_M quantization.',
    'Host CPU: AMD Ryzen 7 7700. Temperature 0; one sequential call per item.',
    'API models are pending credentials.',
    '',
    'Results',
    'Model: llama3.1:latest',
    'Correct: 42/50 | Accuracy: 84% | Parse errors: 0 | Timeouts: 0',
    'p50 latency: 2088.49 ms | p95 latency: 2108.35 ms | Output: 0.69 tok/s',
    'Self-hosted estimate: $2.50 per 1,000 requests (assumption marked below).',
    'First three wrong answers: Non-Compete 002; Exclusivity 004; No-Solicit Customers 006.',
    'All eight errors were false negatives; no parse errors or timeouts occurred.'
)
$page2 = Page-Stream @(
    'Choice and operating economics',
    '',
    'There is not yet a three-model choice because the API models are pending credentials.',
    'For the current offline requirement, choose llama3.1:latest: it is local and scored 84%.',
    'Change the choice if an API model materially improves accuracy or p95 at acceptable cost,',
    'or if evaluation on real clauses shows unacceptable false negatives.',
    '',
    'At 100 times this 50-item run, the current estimate is $12.50 for 5,000 requests.',
    'The estimate assumes $0.30/hour and 120 requests/hour.',
    'GPU, memory, power, and measured hourly cost still need to be recorded.',
    'API break-even cannot be calculated until API prices and token usage are available.',
    '',
    'Limitations and next steps',
    'This is a local pipeline baseline, not a final three-model bake-off.',
    'Use 50+ independently sourced contract clauses and have two people verify each label.',
    'Run the same prompt and items on the top and cheap API models when keys are available.',
    'Record exact model names, dates, hardware, measured costs, and update the report.'
)

$objects = @(
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    "<< /Length $([Text.Encoding]::ASCII.GetByteCount($page1)) >>`nstream`n$page1`nendstream",
    "<< /Length $([Text.Encoding]::ASCII.GetByteCount($page2)) >>`nstream`n$page2`nendstream"
)

$pdf = "%PDF-1.4`n"
$offsets = @()
for ($index = 0; $index -lt $objects.Count; $index++) {
    $offsets += [Text.Encoding]::ASCII.GetByteCount($pdf)
    $pdf += "$($index + 1) 0 obj`n$($objects[$index])`nendobj`n"
}
$xref = [Text.Encoding]::ASCII.GetByteCount($pdf)
$pdf += "xref`n0 $($objects.Count + 1)`n0000000000 65535 f `n"
foreach ($offset in $offsets) { $pdf += ('{0:D10} 00000 n ' -f $offset) + "`n" }
$pdf += "trailer`n<< /Size $($objects.Count + 1) /Root 1 0 R >>`nstartxref`n$xref`n%%EOF`n"
[IO.File]::WriteAllBytes($output, [Text.Encoding]::ASCII.GetBytes($pdf))
Write-Output "Wrote $output"