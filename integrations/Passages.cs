using System.Numerics;
using System.Text.Json;
using PicoGK;

static class Passages
{
    public static Vector3[] Points(JsonElement route) => route.GetProperty("points").EnumerateArray().Select(p=>new Vector3(p[0].GetSingle(),p[1].GetSingle(),p[2].GetSingle())).ToArray();
    public static Voxels Sweep(IEnumerable<JsonElement> routes,float radius)
    {
        using var lattice=new Lattice();
        foreach(var route in routes)
        {
            var p=Points(route);
            for(int i=1;i<p.Length;i++)lattice.AddBeam(p[i-1],radius,p[i],radius);
        }
        return new Voxels(lattice);
    }
    public static Voxels SweepPoints(JsonElement points,float radius)
    {
        using var lattice=new Lattice();
        var p=points.EnumerateArray().Select(x=>new Vector3(x[0].GetSingle(),x[1].GetSingle(),x[2].GetSingle())).ToArray();
        for(int i=1;i<p.Length;i++)lattice.AddBeam(p[i-1],radius,p[i],radius);
        return new Voxels(lattice);
    }
    public static IEnumerable<JsonElement> Routes(JsonElement cooling) => cooling.GetProperty("paths").EnumerateArray().Concat(cooling.GetProperty("ports").EnumerateArray());
    public static int CheckCenterlines(Voxels solid,JsonElement cooling)
    {
        int samples=0;
        foreach(var route in cooling.GetProperty("paths").EnumerateArray())
        {
            samples+=CheckPoints(solid,route.GetProperty("points"),route.GetProperty("id").GetString()!);
        }
        return samples;
    }
    public static int CheckPoints(Voxels solid,JsonElement points,string id)
    {
        var p=points.EnumerateArray().Select(x=>new Vector3(x[0].GetSingle(),x[1].GetSingle(),x[2].GetSingle())).ToArray();
        int samples=0;
        for(int i=1;i<p.Length;i++)
        {
            int n=Math.Max(1,(int)MathF.Ceiling(Vector3.Distance(p[i-1],p[i])*2));
            for(int j=0;j<=n;j++)
            {
                var q=Vector3.Lerp(p[i-1],p[i],(float)j/n);
                if(solid.bIsInside(q))throw new ArgumentException("Obstructed passage centerline: "+id);
                samples++;
            }
        }
        return samples;
    }

    public static (int sampled,int failed) CheckRadialLigaments(Voxels solid,JsonElement cooling,float minimumMm,float pitchMm)
    {
        int sampled=0,failed=0;
        float offset=cooling.GetProperty("radius_mm").GetSingle()+minimumMm+pitchMm/2;
        foreach(var route in cooling.GetProperty("paths").EnumerateArray())
        {
            if(!route.GetProperty("id").GetString()!.StartsWith("channel_"))continue;
            var points=Points(route);
            // End stations join collector and port cavities; check the channel walls
            // away from those deliberate intersections.
            for(int i=1;i<points.Length-1;i++)
            {
                Vector3 p=points[i];
                Vector3 radial=Vector3.Normalize(new Vector3(p.X,p.Y,0));
                if(!solid.bIsInside(p+offset*radial))failed++;
                if(!solid.bIsInside(p-offset*radial))failed++;
                sampled+=2;
            }
        }
        return (sampled,failed);
    }
}
