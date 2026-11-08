# Material and manufacturing inputs

The local catalog contains 53 candidate materials plus custom input. It is a
small JSON file cached once per server process. No material software packages,
cloud requests or additional meshing dependencies are required.

A material name is not a property dataset. Most records require explicit grade,
process and temperature-specific properties. The 316L entry offers density and
conductivity at 20 C from the linked wrought-product datasheet, explicitly not
printed-part strength or high-temperature data. Selecting a named material
clears unavailable properties; the API requires all four engineering properties.

The core density, conductivity, allowable stress and wall-temperature limit feed
existing mass, thermal and structural screens. Tanks and frame remain separate.
Minimum wall and ligament constraints are applied before geometry generation.
Build volume is screened with a conservative bounding box allowing axis
permutations; it does not perform nesting or splitting. Failed manufacturing
checks participate in candidate ranking, while incomplete checks stay unresolved.

Fit, cold-flow and hot-fire are recorded test purposes. They do not change the
operating loads automatically or establish test approval. No profile is marked
print-ready: process calibration, actual wall/intersection inspection, internal
access, supports and qualification remain unresolved. This library supplies
inputs and checks; it does not replace the legacy assembly generator.

References for material-family discovery:
- https://www.eos.info/metal-solutions/metal-materials
- https://formlabs.com/products/materials/

316L reference property source:
- https://www.thyssenkrupp-materials.co.uk/stainless-steel-316l-14404.html
