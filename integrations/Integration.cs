using System.Numerics;
using System.Text.Json;
using PicoGK;

static partial class Demonstrator
{
    static Vector3 V(JsonElement p)=>new(p[0].GetSingle(),p[1].GetSingle(),p[2].GetSingle());
    public static void Integrate(JsonElement config,string folder)
    {
        using var library=new Library(.1f);
        Library.RegisterGlobalLibrary(library);
        int reference=CheckBooleans();
        var records=new List<object>();
        foreach(var part in config.GetProperty("parts").EnumerateArray())
        {
            string id=part.GetProperty("id").GetString()!;
            using var input=Mesh.mshFromStlFile(Path.Combine(folder,id+".input.stl"),Mesh.EStlUnit.MM);
            using var solid=new Voxels(input);
            foreach(string operation in new[]{"add_meshes","subtract_meshes"})
                if(part.TryGetProperty(operation,out var meshes))foreach(var file in meshes.EnumerateArray())
                {
                    using var mesh=Mesh.mshFromStlFile(Path.Combine(folder,file.GetString()!),Mesh.EStlUnit.MM);
                    using var field=new Voxels(mesh);
                    Boolean(operation=="add_meshes"?"Add":"Subtract",solid,field);
                }
            using var outside=new Lattice();
            using var inside=new Lattice();
            bool hasBores=false;
            foreach(var beam in part.GetProperty("beams").EnumerateArray())
                outside.AddBeam(V(beam[0]),beam[2].GetSingle(),V(beam[1]),beam[3].GetSingle());
            foreach(var route in part.GetProperty("routes").EnumerateArray())
            {
                var points=route.GetProperty("points").EnumerateArray().Select(V).ToArray();
                float outer=route.GetProperty("outer").GetSingle(),bore=route.GetProperty("bore").GetSingle();
                for(int i=1;i<points.Length;i++)
                {
                    outside.AddBeam(points[i-1],outer,points[i],outer);
                    inside.AddBeam(points[i-1],bore,points[i],bore);
                }
                // Cut past rounded outer end caps into each annular coupling.
                // A bore ending at the route endpoint creates a sealed pocket.
                float extension=2*outer;
                if(!route.TryGetProperty("cap_start",out var capStart)||!capStart.GetBoolean())
                    inside.AddBeam(points[0]-extension*Vector3.Normalize(points[1]-points[0]),bore,points[0],bore);
                if(!route.TryGetProperty("cap_end",out var capEnd)||!capEnd.GetBoolean())
                    inside.AddBeam(points[^1],bore,points[^1]+extension*Vector3.Normalize(points[^1]-points[^2]),bore);
                hasBores=true;
            }
            using(var additions=new Voxels(outside))Boolean("Add",solid,additions);
            if(hasBores){using var bores=new Voxels(inside);Boolean("Subtract",solid,bores);}
            if(part.TryGetProperty("cuts",out var cuts))
            {
                using var cutter=new Lattice();
                foreach(var cut in cuts.EnumerateArray())cutter.AddBeam(V(cut[0]),cut[2].GetSingle(),V(cut[1]),cut[2].GetSingle());
                using var cutterField=new Voxels(cutter);Boolean("Subtract",solid,cutterField);
            }
            int contactSamples=0,openSamples=0;
            foreach(var point in part.GetProperty("contact_probes").EnumerateArray())
            {
                if(!solid.bIsInside(V(point)))throw new InvalidOperationException(id+" misses contact "+point);
                contactSamples++;
            }
            foreach(var point in part.GetProperty("open_probes").EnumerateArray())
            {
                if(solid.bIsInside(V(point)))throw new InvalidOperationException(id+" blocks passage "+point);
                openSamples++;
            }
            int removed=Save(solid,Path.Combine(folder,id+".stl"));
            records.Add(new {id,voxel_mm=.1,triangle_input_count=input.nTriangleCount(),contact_samples=contactSamples,
                open_samples=openSamples,zero_area_triangles_removed=removed});
            Console.WriteLine($"Integrated {id}: {contactSamples} material probes / {openSamples} open probes");
        }
        File.WriteAllText(Path.Combine(folder,"integration-native.json"),JsonSerializer.Serialize(new {
            voxel_mm=.1,boolean_reference_samples=reference,boolean_operations=BooleanCounts,components=records}));
    }
}
