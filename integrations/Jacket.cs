using System.Numerics;
using System.Text.Json;
using PicoGK;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;
using Leap71.AperiodicTiling;

// Bounded exploratory geometry, deliberately outside the pressure-wall domain.
static class Jacket
{
    public static Voxels Build(JsonElement j,List<object> calls)
    {
        float ri=j.GetProperty("inner_radius_mm").GetSingle(),ro=j.GetProperty("outer_radius_mm").GetSingle();
        float start=j.GetProperty("start_mm").GetSingle(),end=j.GetProperty("end_mm").GetSingle();
        float cell=j.GetProperty("cell_size_mm").GetSingle(),beam=j.GetProperty("beam_radius_mm").GetSingle();
        string pattern=j.GetProperty("pattern").GetString()!;
        using var bounds=new BasePipe(new LocalFrame(new Vector3(0,0,start)),end-start,ri,ro).voxConstruct();
        Voxels result;
        if(pattern=="bcc")
        {
            var cells=new RegularCellArray(bounds,cell,cell,cell,0);
            var type=new BodyCentreLattice();var thickness=new ConstantBeamThickness(beam);
            thickness.SetBoundingVoxels(bounds);var lattice=new Lattice();
            foreach(var unit in cells.aGetUnitCells()){thickness.UpdateCell(unit);type.AddCell(ref lattice,unit,thickness,2);}
            result=new Voxels(lattice);lattice.Dispose();
            calls.Add(new {library="LatticeLibrary",operation="RegularCellArray + BodyCentreLattice + ConstantBeamThickness",status="executed"});
        }
        else if(pattern=="quasi")
        {
            // A bounded cluster is repeated axially; the whole jacket is not a single infinite quasicrystal.
            result=new Voxels();
            for(float z=start;z<=end;z+=2*cell)
            {
                var crystal=new QuasiCrystal(2,new List<QuasiTile>{new QuasiTile_02(new LocalFrame(new Vector3(0,0,z)),ro)});
                using var cluster=crystal.voxGetWireframe(1,beam);result.BoolAdd(cluster);
            }
            calls.Add(new {library="QuasiCrystals",operation="QuasiCrystal generation 1 wireframe; axially repeated clusters",status="executed"});
        }
        else if(pattern=="penrose")
        {
            // Use the upstream public tile inflation API; PenrosePattern's preview method needs a viewer.
            var tiles=new List<ISubDTile>();
            for(int k=0;k<5;k++)
            {
                float a=2*MathF.PI*k/5;Vector3 b=new(ro*MathF.Cos(a),ro*MathF.Sin(a),0);
                Vector3 c=b+Vector3.Transform(-b,Quaternion.CreateFromAxisAngle(Vector3.UnitZ,108*MathF.PI/180));
                tiles.Add(new LargeRhombicTile(new RobinsonTriangle(Vector3.Zero,b,c)));
            }
            for(int gen=0;gen<2;gen++)tiles=tiles.SelectMany(t=>t.aGetInflatedSubTiles()).ToList();
            using var lattice=new Lattice();
            for(float z=start;z<=end;z+=cell)
                foreach(var tile in tiles)
                {
                    var points=tile.aGetTileVertices();
                    for(int k=0;k<points.Count;k++)
                    {
                        Vector3 a=points[k]+new Vector3(0,0,z),b=points[(k+1)%points.Count]+new Vector3(0,0,z);
                        lattice.AddBeam(a,beam,b,beam);
                        if(z+cell<=end)lattice.AddBeam(a,beam,a+new Vector3(0,0,cell),beam);
                    }
                }
            result=new Voxels(lattice);
            calls.Add(new {library="QuasiCrystals / PenrosePattern",operation="LargeRhombicTile + RobinsonTriangle + ISubDTile inflation; stacked planar layers",status="executed"});
        }
        else throw new ArgumentException("Unknown jacket pattern");
        result.BoolIntersect(bounds);return result;
    }
}
