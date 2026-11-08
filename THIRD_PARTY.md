# Third-party sources

Vega's new `packages/vega-geometry` source is a separate original component-graph
and station-loft implementation. It contains no copied PicoGK code.
`vega/inlet.py` independently implements the NASA equations cited in
`docs/GEOMETRY_SOURCES.md`. The parent application still executes PicoGK for its
pressure-fed assembly; that backend is not represented as Vega-owned code.

LEAP 71 develops and owns the upstream PicoGK, LEAP71_ShapeKernel, LEAP71_LatticeLibrary, and LEAP71_QuasiCrystals sources preserved under `vendor/`. See each repository's `LICENSE`, per-file notices, and `vendor/libraries.lock.json` for exact versions and attribution. Library licenses are Apache-2.0; some example files use CC0 notices. Included native binaries have their upstream notices and dependencies.

The optional native build restores SkiaSharp and Microsoft SourceLink build dependencies through NuGet. Their license notices remain in the downloaded packages. The local .NET SDK and its notices live under `.tools/dotnet/`.

LEAP 71's downloadable model catalog is linked for reference only. No model archive or Noyron proprietary engine model is included. Vega is an independent research application and is not affiliated with or endorsed by LEAP 71.

Cantera 3.2.0, its supplied thermodynamic mechanism data, NumPy 2.4.4, ruamel.yaml, and typing_extensions remain installed under `.tools/python`. Their upstream license and package notices are preserved there. These general-purpose dependencies are not used by the current ideal-gas rocket model.
