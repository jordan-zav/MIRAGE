# Reproducing the research models

No weights are distributed with MIRAGE, its source archive, QGIS ZIP or the release-preparation deliverable. These are instructions for a separate, explicitly authorized research run, not an automatic installation step. The 1.3.0 preparation did not train or reevaluate anything.

## License and provenance

TEED source is pinned to [40fa4b1391dc6424f88989d0ca75d5b592c8681d](https://github.com/xavysp/TEED/tree/40fa4b1391dc6424f88989d0ca75d5b592c8681d). Its code is MIT. The original checkpoint checkpoints/BIPED/7/7_model.pth is tracked there, but a separate checkpoint-specific permission is not confirmed. Earlier manifests record repository-wide MIT as their basis, not a separately granted weight license. Confirm rights before redistributing original or derived models. Hashes establish byte identity, not permission.

The original checkpoint SHA-256 is d0109e7f40e7d9f1f495d34947eb08167e8fbb0a13b4e6ab3121261fb8d5a416. Source file and model hashes are retained in [expected_hashes.json](expected_hashes.json). No download runs during package import or extraction.

## Inputs and commands

Use the scripts from scientific source commit 126ba1bfaf0941789c7088a9727ca55ecae4dec2 with the release's portable train_expanded.py arguments. Install MIRAGE development/io/wavelets/nn extras plus PyTorch, ONNX and requests in a separate research environment. Review upstream CUDA/determinism compatibility; package extras deliberately do not install training frameworks.

Use a fresh research-session directory for generated data, weights and logs, and an external TEED source directory. Commands below use relative, user-selected locations. Do not run them to install MIRAGE.

~~~shell
python scripts/research_lineaments.py research-session third-party-sources
python scripts/bank_expanded.py research-session/bank-complete
python scripts/train_expanded.py research-session --teed-source third-party-sources/TEED --pretrained-weights research-session/models/teed-pretrained.pth
python scripts/train_expanded.py research-session --teed-source third-party-sources/TEED --pretrained-weights research-session/models/teed-pretrained.pth --continue-until-stable
~~~

research_lineaments.py explicitly obtains research sources and weights, verifies pinned Git blobs and SHA-256, and writes research_sources.json. Review its scope first: it also records other methods' license notices. The TEED loader removes only an unused reporting import via AST. Network architecture is retained (58,910 parameters).

The bank uses 3,000 independent 128 Ã— 128 Harmonica prism scenes, scene seed 941113 + 104729 Ã— scene ID; train 0â€“1799, validation 1800â€“2399 and test 2400â€“2999. Contact, fault, dike, finite body and crossing geometries cover gravity, TMI and RTP. Verify every scene against the bank manifest. Expected manifest SHA-256: beea91f002d146256491b3a0a280c66bb82fdcae5d8f630aed5495b93a4a0096.

## Budget and selection

Seeds 20261115, 20261116 and 20261117 share the same original initialization. Adam: learning rate 0.0001, weight decay 0.00001; weighted BCE positive weight 12, mean of all four outputs in training and validation, batch size 16. Deterministic rotations/reflections and amplitude 0.8â€“1.2; at most four CPU threads. The observed training used CUDA with CUBLAS_WORKSPACE_CONFIG=:4096:8.

Run the initial 150-epoch stage, then the preregistered continuation. At continuation epoch 151, load the best validation checkpoint and restart Adam with unchanged hyperparameters; the script preserves training-initial logs. Total maximum 900 epochs and 10,800 seconds per seed, patience 15, relative improvement 0.001, minimum 20 epochs before stopping. Stable means the operational validation stopping rule, not proof of mathematical convergence.

Observed runs: 320/319/241 epochs, selected epochs 315/314/236, validation BCE 0.339266/0.339438/0.343153 (rounded), approximately 427/417/320 seconds. Select seed 20261115 by validation BCE alone. Exact logs and runtime versions belong to the archived campaign, not a promise of binary reproducibility across CUDA/PyTorch versions.

Export uses ONNX opset 17, dynamic spatial axes and the final sigmoid output. Validate ONNX Runtime CPU against five validation inputs: atol 1e-5, rtol 1e-4; observed max absolute errors 1.97e-6/1.67e-6/1.67e-6. Exact checkpoint and ONNX hashes for each seed appear in expected_hashes.json. Reproduction on a different dependency/GPU stack can produce different bytes; compare numerics and log the environment rather than claiming a matching hash without checking.

## Evaluation, separate from training

After sealing validation parameters, scripts/evaluate_expanded.py selects thresholds and evaluates complete test scenes. scripts/public_regions.py obtains licensed public inputs, and scripts/evaluate_public.py measures fault-map concordance at the frozen bounds and thresholds. See the [protocol](PROTOCOLO_BANCOS_MEJORA_20261115.md), [budget amendment](ENMIENDA_PRESUPUESTO_20261115.md), [regions](REGIONES_CONGELADAS_20261115.md) and [Pilbara correction](ENMIENDA_PILBARA_20261115.md). These evaluation scripts are documented, not invoked during release preparation.

The historical parameters-locked-before-test.json SHA-256 is 1ff0ec159b7b38f7643506cf0602a8579780321e78362460a9306b3529ae4464. Preserve that artifact as evidence; rerunning evaluation can change serialized metadata such as model paths even when numerical parameters agree. Do not relabel a regenerated file as byte-identical. The packaged calibration JSON remains unchanged and resolves its protocol identifier through the research index.

The combined synthetic criterion requires a positive F1 confidence interval and position noninferiority within 0.5 cells; real concordance requires coverage gain, limited unmatched density and angular noninferiority. B failed both combined criteria and stays experimental. These banks concern geophysics only, and neither route identifies geological origin.
