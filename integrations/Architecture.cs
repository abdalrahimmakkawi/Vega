using System.Numerics;
using System.Text.Json;
using PicoGK;

static partial class Demonstrator
{
    public static void Architecture(JsonElement config,string folder)
    {
        using var library=new Library(.1f);
        Library.RegisterGlobalLibrary(library);
        int reference=CheckBooleans();
        var records=new List<object>();
        foreach(var part in config.GetProperty("modules").EnumerateArray())
        {
            string id=part.GetProperty("id").GetString()!;
            string kind=part.GetProperty("kind").GetString()!;
            var c=part.GetProperty("center_mm");
            var center=new Vector3(c[0].GetSingle(),c[1].GetSingle(),0);
            using var input=Mesh.mshFromStlFile(Path.Combine(folder,id+".input.stl"),Mesh.EStlUnit.MM);
            using var voxels=new Voxels(input);
            if(kind=="heat-exchanger" || kind=="valve")
            {
                var rows=part.GetProperty("profile");
                float start=rows[0][0].GetSingle(),end=rows[rows.GetArrayLength()-1][0].GetSingle(),r=rows[0][1].GetSingle();
                using var lattice=new Lattice();
                if(kind=="heat-exchanger")
                    for(float z=start+2;z<end-1;z+=3)
                        for(int i=0;i<48;i++)
                        {
                            float a=2*MathF.PI*i/48,b=2*MathF.PI*(i+1)/48;
                            lattice.AddBeam(center+new Vector3(r*MathF.Cos(a),r*MathF.Sin(a),z),.6f,
                                center+new Vector3(r*MathF.Cos(b),r*MathF.Sin(b),z),.6f);
                        }
                else
                {
                    float z=(start+end)/2;
                    lattice.AddBeam(center+new Vector3(r-.4f,0,z),1,center+new Vector3(r+5,0,z),1);
                    lattice.AddBeam(center+new Vector3(r+5,-3,z),.8f,center+new Vector3(r+5,3,z),.8f);
                }
                using var details=new Voxels(lattice);Boolean("Add",voxels,details);
            }
            if(kind=="rotor")
            {
                float start=part.GetProperty("z_start").GetSingle(),end=part.GetProperty("z_end").GetSingle();
                float hub=part.GetProperty("hub_outer").GetSingle(),tip=part.GetProperty("tip_radius").GetSingle();
                int count=part.GetProperty("blade_count").GetInt32();
                using var blades=new Voxels(new Field(p=>{
                    var q=p-center;float r=new Vector2(q.X,q.Y).Length(),theta=MathF.Atan2(q.Y,q.X);
                    float a=theta-.4f*(p.Z-start)/(end-start);
                    float nearest=MathF.Abs(MathF.Atan2(MathF.Sin(a*count),MathF.Cos(a*count)))/count;
                    return MathF.Max(MathF.Max(start-p.Z,p.Z-end),MathF.Max(MathF.Max(hub-.6f-r,r-tip),nearest*r-.65f));
                }),new BBox3(center+new Vector3(-tip-1,-tip-1,start-1),center+new Vector3(tip+1,tip+1,end+1)));
                Boolean("Add",voxels,blades);
            }
            if(kind=="regenerator")
            {
                using var lattice=new Lattice();
                lattice.AddBeam(new Vector3(center.X,-10,60),1.8f,new Vector3(center.X,10,60),1.8f);
                // Repeated ribs distinguish the paired heat-storage canisters.
                foreach(float y in new[]{-10f,10f})for(float z=50;z<=72;z+=4)
                    for(int i=0;i<48;i++)
                    {
                        float a=2*MathF.PI*i/48,b=2*MathF.PI*(i+1)/48;
                        lattice.AddBeam(new Vector3(center.X+5.2f*MathF.Cos(a),y+5.2f*MathF.Sin(a),z),.6f,
                            new Vector3(center.X+5.2f*MathF.Cos(b),y+5.2f*MathF.Sin(b),z),.6f);
                    }
                using var ribs=new Voxels(lattice);Boolean("Add",voxels,ribs);
            }
            if(kind=="shield")
            {
                using var rearHalf=new Voxels(new Field(p=>p.Y),new BBox3(new Vector3(-31,-31,119),new Vector3(31,31,179)));
                Boolean("Intersect",voxels,rearHalf);
            }
            if(kind=="can"||kind=="pump")
            {
                float z=part.GetProperty("port_z").GetSingle(),r=part.GetProperty("outer_radius").GetSingle();
                using var fittings=new Lattice();
                fittings.AddBeam(center+new Vector3(r-.6f,0,z),1.2f,center+new Vector3(r+4,0,z),1.2f);
                using var ports=new Voxels(fittings);Boolean("Add",voxels,ports);
            }
            int removed=Save(voxels,Path.Combine(folder,id+".stl"));
            records.Add(new {id,voxel_mm=.1,triangle_input_count=input.nTriangleCount(),zero_area_triangles_removed=removed});
            Console.WriteLine($"Exported {id} at 0.1 mm");
        }
        File.WriteAllText(Path.Combine(folder,"architecture-native.json"),JsonSerializer.Serialize(new {
            voxel_mm=.1,boolean_reference_samples=reference,boolean_operations=BooleanCounts,components=records,
            geometry_pipeline="triangle_mesh_to_voxels_then_implicit_booleans",scope="Non-firing architecture representations"}));
    }
}
