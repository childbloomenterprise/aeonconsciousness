# Observer Architecture

Sakshin reads signed runtime events and compares claimed memory influence against retrieval telemetry. Model Behaviour Observer stores request/context hashes, supplied structured-state keys, provider/model identity, output hashes, usage, timing, and errors. Hosted-model hidden states remain unavailable. Mismatches can indicate possible confabulation, telemetry gaps, lag, or tampering.

