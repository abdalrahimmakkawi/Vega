using System.Numerics;
using System.Text.Json;
using PicoGK;
static partial class Demonstrator
{
    public static void ProbeAssembly(JsonElement config,string folder)
    {
        using var library=new Library(.1f);Library.RegisterGlobalLibrary(library);
        var records=new List<object>();
        foreach(var item in config.GetProperty("parts").EnumerateArray())
        {
            using var mesh=Mesh.mshFromStlFile(Path.Combine(folder,item.GetProperty("file").GetString()!),Mesh.EStlUnit.MM);
            using var voxels=new Voxels(mesh);var blocked=new List<int>();int count=0;
            foreach(var probe in item.GetProperty("probes").EnumerateArray())
            {
                bool expected=probe.TryGetProperty("expected_inside",out var expectedValue)&&expectedValue.GetBoolean();
                if(voxels.bIsInside(V(probe.GetProperty("point")))!=expected)blocked.Add(probe.GetProperty("index").GetInt32());
                count++;
            }
            records.Add(new{file=item.GetProperty("file").GetString(),samples=count,blocked});
            Console.WriteLine("Passage check "+item.GetProperty("file").GetString()+": "+blocked.Count+" / "+count+" blocked");
        }
        File.WriteAllText(Path.Combine(folder,"assembly-passage-checks.json"),JsonSerializer.Serialize(records));
    }
    public static void RoutingGrid(JsonElement config,string folder)
    {
        using var library=new Library(.5f);Library.RegisterGlobalLibrary(library);
        var lo=V(config.GetProperty("origin"));float step=config.GetProperty("step").GetSingle();
        var shape=config.GetProperty("shape");int nx=shape[0].GetInt32(),ny=shape[1].GetInt32(),nz=shape[2].GetInt32();
        var grid=new byte[nx*ny*nz];float margin=config.GetProperty("margin").GetSingle();
        foreach(var item in config.GetProperty("parts").EnumerateArray())
        {
            using var mesh=Mesh.mshFromStlFile(Path.Combine(folder,item.GetProperty("file").GetString()!),Mesh.EStlUnit.MM);
            using var voxels=new Voxels(mesh);voxels.Offset(margin);
            var bounds=item.GetProperty("bounds");var a=V(bounds[0])-new Vector3(margin+1);var b=V(bounds[1])+new Vector3(margin+1);
            for(int x=Math.Max(0,(int)MathF.Floor((a.X-lo.X)/step));x<=Math.Min(nx-1,(int)MathF.Ceiling((b.X-lo.X)/step));x++)
            for(int y=Math.Max(0,(int)MathF.Floor((a.Y-lo.Y)/step));y<=Math.Min(ny-1,(int)MathF.Ceiling((b.Y-lo.Y)/step));y++)
            for(int z=Math.Max(0,(int)MathF.Floor((a.Z-lo.Z)/step));z<=Math.Min(nz-1,(int)MathF.Ceiling((b.Z-lo.Z)/step));z++)
                if(voxels.bIsInside(lo+step*new Vector3(x,y,z)))grid[(x*ny+y)*nz+z]=1;
            Console.WriteLine("Routing obstacle "+item.GetProperty("file").GetString());
        }
        File.WriteAllBytes(Path.Combine(folder,"routing-grid.bin"),grid);
    }
}
