# Research notes

The local Phase 5.5 research protocol and benchmark YAML govern this implementation. They specify the graph nulls, GRU size/search budget, calibration and primary/secondary comparisons. The Phase 8 v1.1/v1.2 amendments authorize the next-float threshold policy and synthetic mappings. Phase 9 defines a separate engineered world; it does not supersede the open-loop primary endpoint or supply a validated directional target for a supervised baseline.

Primary sources consulted in this session:

- Cho et al., [Learning Phrase Representations using RNN Encoder–Decoder](https://arxiv.org/abs/1406.1078): gated recurrent equations. We use reset-before candidate `n=tanh(xWn+(r*h)Un+bn)`, gates `r=sigmoid(xWr+hUr+br)`, `z=sigmoid(xWz+hUz+bz)`, and `h'=(1-z)h+z*n`. Gate naming conventions vary; these explicit equations are the contract.
- Kingma and Ba, [Adam: A Method for Stochastic Optimization](https://arxiv.org/abs/1412.6980): first/second moments with bias correction. The local implementation uses beta1=.9, beta2=.999, epsilon=1e-8 and the predeclared two learning rates. Full analytical gradients are checked by central finite differences, not assumed correct from implementation alone.

NumPy, pytest, matplotlib, SciPy and PyYAML are already installed in the requested venv; PyTorch/TensorFlow are not. NumPy BPTT avoids adding dependencies. The implementation uses no external ML framework, no pretrained model and no downloaded dataset. No new dependency was installed.
