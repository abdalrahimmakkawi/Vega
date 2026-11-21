using System.Numerics;
using System.Text.Json;
using PicoGK;

static partial class Demonstrator
{
    static float PolylineDistance(Vector3 p,Vector3[] points)
    {
        float result=float.MaxValue;
        for(int i=1;i<points.Length;i++){
            var d=points[i]-points[i-1];float t=Math.Clamp(Vector3.Dot(p-points[i-1],d)/d.LengthSquared(),0,1);
            result=MathF.Min(result,Vector3.Distance(p,points[i-1]+t*d));
        }
        return result;
    }
    public static void Cooling(JsonElement config,string folder)
    {
        using var library=new Library(.1f);Library.RegisterGlobalLibrary(library);
        int reference=CheckBooleans();
        using var mesh=Mesh.mshFromStlFile(Path.Combine(folder,"cooling-manifolds.input.stl"),Mesh.EStlUnit.MM);
        using var jacket=new Voxels(mesh);using var outside=new Lattice();using var inside=new Lattice();
        int samples=0;
        foreach(var route in config.GetProperty("routes").EnumerateArray()){
            var points=route.GetProperty("points").EnumerateArray().Select(V).ToArray();
            float radius=route.GetProperty("outer_radius_mm").GetSingle(),bore=route.GetProperty("bore_radius_mm").GetSingle();
            for(int i=1;i<points.Length;i++){
                outside.AddBeam(points[i-1],radius,points[i],radius);
                inside.AddBeam(points[i-1],bore,points[i],bore);
            }
            if(route.TryGetProperty("open_end",out var openEnd) && openEnd.GetBoolean())
                inside.AddBeam(points[^1],bore,points[^1]+2*radius*Vector3.Normalize(points[^1]-points[^2]),bore);
        }
        using(var additions=new Voxels(outside))Boolean("Add",jacket,additions);
        using(var bores=new Voxels(inside))Boolean("Subtract",jacket,bores);
        foreach(var point in config.GetProperty("open_probes").EnumerateArray()){
            if(jacket.bIsInside(V(point)))throw new InvalidOperationException("Cooling passage blocked at "+point);
            samples++;
        }
        var records=new List<object>();
        foreach(int side in new[]{1,-1}){
            using var half=new Voxels(jacket);
            using var clip=new Voxels(new Field(p=>-side*p.Y-.2f),new BBox3(new(-26,-26,138),new(26,26,186)));
            Boolean("Intersect",half,clip);
            string id=side==1?"bell-cooling-a":"bell-cooling-b";
            foreach(var point in config.GetProperty(id+"_contacts").EnumerateArray())
                if(!half.bIsInside(V(point)))throw new InvalidOperationException(id+" misses attachment "+point);
            int removed=Save(half,Path.Combine(folder,id+".stl"));
            records.Add(new {id,voxel_mm=.1,zero_area_triangles_removed=removed});
            Console.WriteLine("Exported "+id);
        }
        File.WriteAllText(Path.Combine(folder,"cooling-native.json"),JsonSerializer.Serialize(new {
            voxel_mm=.1,triangle_input_count=mesh.nTriangleCount(),boolean_reference_samples=reference,
            boolean_operations=BooleanCounts,open_samples=samples,components=records}));
    }
    public static void CoolingDetail(JsonElement config,string folder)
    {
        using var library=new Library(.009f);Library.RegisterGlobalLibrary(library);
        int reference=CheckBooleans(.1f);
        var center=V(config.GetProperty("center_mm"));var half=Vector3.One*config.GetProperty("crop_size_mm").GetSingle()/2;
        var bounds=new BBox3(center-half,center+half);
        var points=config.GetProperty("points").EnumerateArray().Select(V).ToArray();
        using var input=Mesh.mshFromStlFile(Path.Combine(folder,"cooling-detail.input.stl"),Mesh.EStlUnit.MM);
        using var solid=new Voxels(input);
        using var outer=new Voxels(new Field(p=>PolylineDistance(p,points)-1.8f),bounds);
        using var bore=new Voxels(new Field(p=>PolylineDistance(p,points)-.7f),bounds);
        Boolean("Intersect",solid,outer);Boolean("Subtract",solid,bore);
        int removed=Save(solid,Path.Combine(folder,"cooling-detail.stl"));
        File.WriteAllText(Path.Combine(folder,"cooling-detail-native.json"),JsonSerializer.Serialize(new {
            voxel_mm=.009,triangle_input_count=input.nTriangleCount(),boolean_reference_samples=reference,
            boolean_operations=BooleanCounts,zero_area_triangles_removed=removed}));
    }
}
