using System.Numerics;
using System.Text.Json;
using PicoGK;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;

// A bounded material field, not a combustion or pressure-vessel design.
static partial class Demonstrator
{
    static readonly Dictionary<string,int> BooleanCounts=new(){{"Add",0},{"Subtract",0},{"Intersect",0}};
    static void Boolean(string operation,Voxels target,Voxels operand)
    {
        try
        {
            switch(operation)
            {
                case "Add":target.BoolAdd(operand);break;
                case "Subtract":target.BoolSubtract(operand);break;
                case "Intersect":target.BoolIntersect(operand);break;
                default:throw new ArgumentException("Unknown Boolean operation");
            }
            BooleanCounts[operation]++;
        }
        catch(Exception error)
        {
            throw new InvalidOperationException($"PicoGK Boolean {operation} failed; build cannot be published",error);
        }
    }
    static int CheckBooleans(float scale=1)
    {
        var box=new BBox3(scale*new Vector3(-4,-4,-4),scale*new Vector3(6,4,4));
        float Cube(Vector3 p)=>MathF.Max(MathF.Abs(p.X),MathF.Max(MathF.Abs(p.Y),MathF.Abs(p.Z)))-2*scale;
        using var a=new Voxels(new Field(p=>Cube(p)),box);
        using var b=new Voxels(new Field(p=>Cube(p-scale*new Vector3(2,0,0))),box);
        Vector3[] probes={new(-1,0,0),new(1,0,0),new(3,0,0),new(5,0,0),new(1,3,0)};
        bool[][] expected={new[]{true,true,true,false,false},new[]{true,false,false,false,false},new[]{false,true,false,false,false}};
        int samples=0,index=0;
        foreach(string op in new[]{"Add","Subtract","Intersect"})
        {
            using var result=new Voxels(a);
            Boolean(op,result,b);
            for(int i=0;i<probes.Length;i++)
            {
                if(result.bIsInside(scale*probes[i])!=expected[index][i])
                    throw new InvalidOperationException($"Boolean {op} reference test failed at {probes[i]}");
                samples++;
            }
            index++;
        }
        foreach(string op in new[]{"Add","Subtract","Intersect"})BooleanCounts[op]=0;
        return samples;
    }
    static int Save(Voxels voxels,string path)
    {
        using var source=voxels.mshAsMesh();
        // Stream the binary STL instead of duplicating millions of triangles
        // in a second native mesh. Fine voxel exports otherwise exhaust RAM
        // and force Windows to grow its page file during generation.
        using var file=File.Create(path);
        using var output=new BinaryWriter(file);
        output.Write(new byte[80]);output.Write((uint)0);
        int removed=0,kept=0;
        void Vector(Vector3 v){output.Write(v.X);output.Write(v.Y);output.Write(v.Z);}
        for(int i=0;i<source.nTriangleCount();i++)
        {
            source.GetTriangle(i,out var a,out var b,out var c);
            float area=Vector3.Cross(b-a,c-a).LengthSquared();
            if(!float.IsFinite(area))throw new InvalidOperationException("Nonfinite native vertex");
            if(area==0){removed++;continue;}
            Vector(Vector3.Normalize(Vector3.Cross(b-a,c-a)));Vector(a);Vector(b);Vector(c);output.Write((ushort)0);kept++;
        }
        file.Position=80;output.Write((uint)kept);
        return removed;
    }
    sealed class Field(Func<Vector3, float> evaluate) : IImplicit
    {
        public float fSignedDistance(in Vector3 p) => evaluate(p);
    }
    static float CentrebodyRadius(float z)
    {
        if(z<-6)return .8f+(z+22)*.25f;
        if(z<6)return 4.8f+(z+6)*(3.2f/12);
        if(z<16)return 8;
        if(z<20)return 8-(z-16)*1.5f;
        return 2;
    }
    static float CentrebodyDistance(Vector3 p,float travel)
    {
        float z=p.Z-travel;
        return MathF.Max(MathF.Max(-22-z,z-64),new Vector2(p.X,p.Y).Length()-CentrebodyRadius(z));
    }
    public static void Detail(JsonElement recipe,string folder)
    {
        using var library=new Library(.01f);
        Library.RegisterGlobalLibrary(library);
        float travel=recipe.GetProperty("intake").GetProperty("centrebody_mm").GetSingle();
        var center=new Vector3(4.8f,0,-6+travel);
        using var detail=new Voxels(new Field(p=>MathF.Max(CentrebodyDistance(p,travel),
            MathF.Max(MathF.Abs(p.X-center.X),MathF.Max(MathF.Abs(p.Y-center.Y),MathF.Abs(p.Z-center.Z)))-1)),
            new BBox3(center-new Vector3(1.1f),center+new Vector3(1.1f)));
        Save(detail,Path.Combine(folder,"intake-detail.stl"));
        File.WriteAllText(Path.Combine(folder,"detail.json"),JsonSerializer.Serialize(new {
            voxel_mm=.01f,scope="2 mm cube at the two-cone junction; closed crop boundaries are artificial",center_mm=new[]{center.X,center.Y,center.Z}}));
    }
    static void SystemModules(string folder)
    {
        // Static architecture models. No rotor performance or fuel handling
        // capability is inferred from these blade and casing representations.
        using(var hub=new BasePipe(new LocalFrame(new Vector3(0,0,50)),10,9,11).voxConstruct())
        {
            using var blades=new Lattice();
            for(int i=0;i<4;i++)for(int j=0;j<5;j++)
            {
                float z=51+j*1.6f,angle=MathF.PI/4+i*MathF.PI/2;
                blades.AddBeam(new Vector3(10*MathF.Cos(angle),10*MathF.Sin(angle),z),1.1f,
                    new Vector3(21*MathF.Cos(angle+.18f),21*MathF.Sin(angle+.18f),z+1),1.1f);
            }
            using var bv=new Voxels(blades);Boolean("Add",hub,bv);
            Save(hub,Path.Combine(folder,"air-compressor.raw.stl"));
        }
        foreach(var module in new[]{("helium-circulator",new Vector3(-38,0,40)),("hydrogen-pump",new Vector3(38,0,68))})
        {
            var c=module.Item2;
            using var body=new Voxels(new Field(p=>MathF.Max(new Vector2(p.X-c.X,p.Y-c.Y).Length()-7,
                MathF.Abs(p.Z-c.Z)-5)),new BBox3(c-new Vector3(13,13,10),c+new Vector3(13,13,12)));
            using var features=new Lattice();
            features.AddBeam(c-new Vector3(0,0,7),2.5f,c+new Vector3(0,0,9),2.5f);
            features.AddBeam(c+new Vector3(5,0,0),1.8f,c+new Vector3(11,0,0),1.8f);
            for(int i=0;i<8;i++)
            {
                float a=i*MathF.PI/4;
                features.AddBeam(c+new Vector3(2*MathF.Cos(a),2*MathF.Sin(a),-5.5f),.8f,
                    c+new Vector3(6*MathF.Cos(a+.28f),6*MathF.Sin(a+.28f),-5.5f),.8f);
            }
            using var fv=new Voxels(features);Boolean("Add",body,fv);
            Save(body,Path.Combine(folder,module.Item1+".raw.stl"));
        }
    }
    static Voxels Sweep(JsonElement points,float radius)
    {
        var vertices=points.EnumerateArray().Select(p=>new Vector3(p[0].GetSingle(),p[1].GetSingle(),p[2].GetSingle())).ToArray();
        using var lattice=new Lattice();
        for(int i=1;i<vertices.Length;i++)lattice.AddBeam(vertices[i-1],radius,vertices[i],radius);
        return new Voxels(lattice);
    }

    sealed class Profile
    {
        readonly float[][] radii;
        public readonly float End;
        public readonly float Start;
        public Profile(JsonElement rows)
        {
            radii=rows.EnumerateArray().Select(r=>r.GetProperty("radii_mm").EnumerateArray().Select(v=>v.GetSingle()).ToArray()).ToArray();
            End=rows[rows.GetArrayLength()-1].GetProperty("z_mm").GetSingle();
            Start=rows[0].GetProperty("z_mm").GetSingle();
        }
        public float Radius(Vector3 p)
        {
            float z=Math.Clamp(p.Z,Start,End)-Start, angle=MathF.Atan2(p.Y,p.X);
            if(angle<0)angle+=2*MathF.PI;
            float u=angle*radii[0].Length/(2*MathF.PI);
            int i=Math.Min((int)z,radii.Length-2), j=(int)u%radii[0].Length, k=(j+1)%radii[0].Length;
            float f=u-MathF.Floor(u), t=z-i;
            return (1-t)*(radii[i][j]*(1-f)+radii[i][k]*f)+t*(radii[i+1][j]*(1-f)+radii[i+1][k]*f);
        }
        public float Shell(Vector3 p,float wall) => MathF.Max(
            MathF.Max(Start-p.Z,p.Z-End),MathF.Abs(new Vector2(p.X,p.Y).Length()-Radius(p)-wall/2)-wall/2);
    }

    public static void Build(JsonElement recipe, string folder, float pitch)
    {
        Directory.CreateDirectory(folder);
        using var library=new Library(pitch);
        Library.RegisterGlobalLibrary(library);
        int booleanReferenceSamples=CheckBooleans();
        Console.WriteLine($"Add, Subtract and Intersect reference checks passed ({booleanReferenceSamples} probes)");
        var bounds=new BBox3(new Vector3(-34,-34,-2),new Vector3(34,34,122));
        var outer=new Profile(recipe.GetProperty("outer"));
        var core=new Profile(recipe.GetProperty("core"));
        float wall=recipe.GetProperty("wall_mm").GetSingle();
        using var inputMesh=Mesh.mshFromStlFile(Path.Combine(folder,"input-body.stl"),Mesh.EStlUnit.MM);
        int inputTriangles=inputMesh.nTriangleCount();
        if(inputTriangles<=0)throw new InvalidOperationException("Empty triangular input mesh");
        using var solid=new Voxels(inputMesh);
        Console.WriteLine($"Voxelized {inputTriangles} input triangles at {pitch} mm");
        float HubRadius(float z)
        {
            float nose=Math.Clamp(z/14,0,1),tail=Math.Clamp((z-44)/18,0,1);
            return 1.2f+6.8f*nose*nose*(3-2*nose)-5*tail*tail*(3-2*tail);
        }
        var intake=recipe.GetProperty("intake");
        float travel=intake.GetProperty("centrebody_mm").GetSingle();
        using(var centrebody=new Voxels(new Field(p=>CentrebodyDistance(p,travel)),
            new BBox3(new Vector3(-9,-9,-27),new Vector3(9,9,69))))
            Save(centrebody,Path.Combine(folder,"centrebody.raw.stl"));
        using(var guide=new BasePipe(new LocalFrame(new Vector3(0,0,48)),14,2.6f,6).voxConstruct())
            Boolean("Add",solid,guide);
        Console.WriteLine("Implicit flow body complete");

        // Four broad vanes support the core. Each longitudinal half retains two.
        using(var beams=new Lattice())
        {
            foreach(float z in new[]{54f,70f})
                for(int i=0;i<4;i++)
                {
                    float a=MathF.PI/4+i*MathF.PI/2;
                    Vector3 d=new(MathF.Cos(a),MathF.Sin(a),0);
                    float inner=z<66?5f:9f;
                    beams.AddBeam(d*inner+Vector3.UnitZ*z,1.4f,d*24+Vector3.UnitZ*(z+4),1.4f);
                }
            using var supports=new Voxels(beams);Boolean("Add",solid,supports);
        }
        // Enlarged solid tube representations, sized by Vega's heat-exchanger
        // area screen. These are not hollow helium tubes or a working cooler.
        var hx=recipe.GetProperty("synthesis").GetProperty("geometry").GetProperty("precooler");
        int tubeCount=hx.GetProperty("tube_count").GetInt32();
        float tubeRadius=hx.GetProperty("tube_diameter_mm").GetSingle()/2;
        float ringRadius=hx.GetProperty("ring_radius_mm").GetSingle();
        float hxStart=24, hxEnd=hxStart+hx.GetProperty("length_mm").GetSingle();
        using(var bundle=new Lattice())
        {
            for(int i=0;i<tubeCount;i++)
            {
                float a=2*MathF.PI*i/tubeCount;
                var radial=new Vector3(ringRadius*MathF.Cos(a),ringRadius*MathF.Sin(a),0);
                bundle.AddBeam(radial+Vector3.UnitZ*hxStart,tubeRadius,radial+Vector3.UnitZ*hxEnd,tubeRadius);
            }
            foreach(float z in new[]{hxStart,hxEnd})
            {
                for(int i=0;i<120;i++)
                {
                    float a=2*MathF.PI*i/120,b=2*MathF.PI*(i+1)/120;
                    bundle.AddBeam(new Vector3(ringRadius*MathF.Cos(a),ringRadius*MathF.Sin(a),z),1.4f,
                        new Vector3(ringRadius*MathF.Cos(b),ringRadius*MathF.Sin(b),z),1.4f);
                }
                for(int i=0;i<4;i++)
                {
                    float a=MathF.PI/4+i*MathF.PI/2;
                    var d=new Vector3(MathF.Cos(a),MathF.Sin(a),0);
                    bundle.AddBeam(d*ringRadius+Vector3.UnitZ*z,1.4f,d*24+Vector3.UnitZ*z,1.4f);
                }
            }
            // Solid transparent-system representations: these routes are not
            // certified helium plumbing. They make the proposed loop visible.
            foreach(float z in new[]{hxStart,hxEnd})
            {
                bundle.AddBeam(new Vector3(-18,0,z),1.2f,new Vector3(-34,0,z),1.2f);
                bundle.AddBeam(new Vector3(-34,0,z),1.2f,new Vector3(-38,0,40),1.2f);
            }
            using var tubeSolid=new Voxels(bundle);
            Save(tubeSolid,Path.Combine(folder,"precooler.raw.stl"));
        }
        SystemModules(folder);

        // Existing LEAP71 implicit TPMS implementation. Its raw pattern is
        // dimensionless; convert the requested band using a conservative bound
        // on its gradient (sqrt(12) * 2*pi / cell). Not an exact distance field.
        float cell=recipe.GetProperty("gyroid_cell_mm").GetSingle();
        float band=recipe.GetProperty("gyroid_min_band_mm").GetSingle();
        var gyroid=new ImplicitModular(new RawGyroidTPMSPattern(),
            new ConstantBeamThickness(band*MathF.Sqrt(12)*2*MathF.PI/cell),
            new ScaleTrafo(cell,cell,cell),new FullWallLogic());
        // Evaluate the bounded implicit directly. IntersectImplicit on an
        // existing shell raises a native SEH exception at 0.3 mm in this build.
        using(var jacket=new Voxels(new Field(p=>MathF.Max(
            MathF.Max(MathF.Max(24-p.Z,p.Z-64),MathF.Abs(new Vector2(p.X,p.Y).Length()-26.5f)-2.5f),
            gyroid.fSignedDistance(p))),new BBox3(new Vector3(-30,-30,23),new Vector3(30,30,65))))
        {
            Boolean("Add",solid,jacket);
        }
        // A continuous overlap land joins the gyroid to the casing. At fine
        // resolution, near-tangent TPMS contacts otherwise enclose long slivers.
        using(var gyroidLand=new Voxels(new Field(p=>MathF.Max(MathF.Max(24-p.Z,p.Z-64),
            MathF.Max(new Vector2(p.X,p.Y).Length()-26.2f,
                outer.Radius(p)+wall-.8f-new Vector2(p.X,p.Y).Length()))),bounds))
            Boolean("Add",solid,gyroidLand);
        // A continuous backing band anchors the BCC cells where the computed
        // intake contracts below the fixed lattice envelope.
        using(var backing=new Voxels(new Field(p=>MathF.Max(MathF.Max(5-p.Z,p.Z-25),
            MathF.Max(new Vector2(p.X,p.Y).Length()-(pitch>=.7f?28.8f:26.6f),
                outer.Radius(p)+wall-1f-new Vector2(p.X,p.Y).Length()))),bounds))
            Boolean("Add",solid,backing);
        using(var jacketBounds=new BasePipe(new LocalFrame(new Vector3(0,0,7)),14,24,29).voxConstruct())
        {
            float bccCell=recipe.GetProperty("bcc_cell_mm").GetSingle();
            var cells=new RegularCellArray(jacketBounds,bccCell,bccCell,bccCell,0);
            var type=new BodyCentreLattice();
            var thickness=new ConstantBeamThickness(recipe.GetProperty("bcc_beam_diameter_mm").GetSingle());
            var lattice=new Lattice();
            try
            {
                foreach(var unit in cells.aGetUnitCells())type.AddCell(ref lattice,unit,thickness,2);
                using var bcc=new Voxels(lattice);Boolean("Intersect",bcc,jacketBounds);Boolean("Add",solid,bcc);
            }
            finally { lattice.Dispose(); }
        }
        // Anchor the bounded lattice ends and provide smooth rubber-band seats.
        foreach(var ring in new[]{(0f,5f,24f,30f),(19f,6f,22f,30f),(62f,5f,22f,30f),(116f,4f,17f,21f)})
        {
            using var collar=new BasePipe(new LocalFrame(new Vector3(0,0,ring.Item1)),ring.Item2,ring.Item3,ring.Item4).voxConstruct();
            Boolean("Add",solid,collar);
        }
        // Anchor lattice ends at the split boundary so neither print half
        // inherits a free beam tip whose attachment was in the other half.
        using(var rails=new Lattice())
        {
            foreach(float x in new[]{-27f,27f})
                rails.AddBeam(new Vector3(x,0,5),2.4f,new Vector3(x,0,25),2.4f);
            using var railSolid=new Voxels(rails);Boolean("Add",solid,railSolid);
        }
        // Preserve open gyroid pores. Recut the central nozzle bore after unions.
        using(var bore=new Voxels(new Field(p=>MathF.Max(MathF.Max(core.Start-p.Z,p.Z-122),new Vector2(p.X,p.Y).Length()-core.Radius(p))),bounds))
            Boolean("Subtract",solid,bore);
        var cooling=recipe.GetProperty("cooling");
        using var coolingBores=new Voxels();
        foreach(string group in new[]{"routes","collectors","ports"})
            foreach(var route in cooling.GetProperty(group).EnumerateArray())
            {
                using var tube=Sweep(route.GetProperty("points"),route.GetProperty("outer_radius_mm").GetSingle());
                Boolean("Add",solid,tube);
                using var bore=Sweep(route.TryGetProperty("bore_points",out var bp)?bp:route.GetProperty("points"),route.GetProperty("bore_radius_mm").GetSingle());
                Boolean("Add",coolingBores,bore);
            }
        Boolean("Subtract",solid,coolingBores);
        int coolingSamples=0, coolingClearanceSamples=0;
        foreach(string group in new[]{"routes","collectors","ports"})
            foreach(var route in cooling.GetProperty(group).EnumerateArray())
            {
                var ps=(route.TryGetProperty("bore_points",out var bp)?bp:route.GetProperty("points")).EnumerateArray()
                    .Select(p=>new Vector3(p[0].GetSingle(),p[1].GetSingle(),p[2].GetSingle())).ToArray();
                for(int i=1;i<ps.Length;i++)
                {
                    int n=Math.Max(1,(int)MathF.Ceiling(Vector3.Distance(ps[i-1],ps[i])/.2f));
                    for(int j=0;j<=n;j++)
                    {
                        var center=Vector3.Lerp(ps[i-1],ps[i],(float)j/n);
                        if(solid.bIsInside(center))
                            throw new InvalidOperationException("Blocked cooling inspection route");
                        coolingSamples++;
                        var tangent=Vector3.Normalize(ps[i]-ps[i-1]);
                        var axis=MathF.Abs(tangent.Z)<.9f?Vector3.UnitZ:Vector3.UnitX;
                        var u=Vector3.Normalize(Vector3.Cross(tangent,axis));
                        var v=Vector3.Cross(tangent,u);
                        for(int k=0;k<8;k++)
                        {
                            float a=2*MathF.PI*k/8;
                            if(solid.bIsInside(center+.4f*(u*MathF.Cos(a)+v*MathF.Sin(a))))
                                throw new InvalidOperationException("Cooling passage fails sampled 0.8 mm diameter clearance");
                            coolingClearanceSamples++;
                        }
                    }
                }
            }
        Console.WriteLine("Gyroid, BCC lattice and collars complete");

        int clear=0, wallSamples=0, portApertureSamples=0;
        for(float z=1;z<120;z+=.5f)
        {
            // Nine samples across the central passage, plus four annular
            // corridors. Sampled clearance only, not a flow or leak solution.
            var points=new List<Vector3>();
            if(z>=66)
            {
                points.Add(new Vector3(0,0,z));
                for(int i=0;i<8;i++)points.Add(new Vector3(1.5f*MathF.Cos(i*MathF.PI/4),1.5f*MathF.Sin(i*MathF.PI/4),z));
            }
            for(int i=0;i<4;i++)
            {
                var p=new Vector3(14.8f*MathF.Cos(i*MathF.PI/2),14.8f*MathF.Sin(i*MathF.PI/2),z);
                points.Add(p);points.Add(p+.6f*Vector3.UnitX);points.Add(p-.6f*Vector3.UnitX);
                points.Add(p+.6f*Vector3.UnitY);points.Add(p-.6f*Vector3.UnitY);
            }
            foreach(var p in points)
            {
                if(solid.bIsInside(p))throw new InvalidOperationException($"Blocked sample at {p}");
                clear++;
            }
            foreach(var profile in new[]{outer,core})
                if(z>profile.Start+1 && z<profile.End-1)
                    for(int i=0;i<24;i++)
                    {
                        var direction=new Vector3(MathF.Cos(i*MathF.PI/12),MathF.Sin(i*MathF.PI/12),0);
                        float radius=profile.Radius(direction+Vector3.UnitZ*z);
                        foreach(float depth in new[]{.6f,1.2f,1.8f})
                        {
                            var sample=direction*(radius+depth)+Vector3.UnitZ*z;
                            if(!solid.bIsInside(sample))
                            {
                                if(profile==outer && coolingBores.bIsInside(sample) &&
                                   (MathF.Abs(z-76)<1.2f || MathF.Abs(z-112)<1.2f))
                                {portApertureSamples++;continue;}
                                throw new InvalidOperationException($"Main wall sample missing at {sample}");
                            }
                            wallSamples++;
                        }
                    }
        }
        int degenerateRemoved=Save(solid,Path.Combine(folder,"assembled.stl"));
        foreach(var (name,side) in new[]{("half-a",1f),("half-b",-1f)})
        {
            using var halfSpace=new Voxels(new Field(p=>MathF.Max(
                MathF.Max(-side*p.Y,side*p.Y-34),MathF.Max(MathF.Abs(p.X)-34,MathF.Max(-2-p.Z,p.Z-122)))),bounds);
            using var half=new Voxels(solid);
            Boolean("Intersect",half,halfSpace);
            degenerateRemoved+=Save(half,Path.Combine(folder,name+".raw.stl"));
        }
        File.WriteAllText(Path.Combine(folder,"native.json"),JsonSerializer.Serialize(new {
            sampled_open_path_points=clear,sampled_wall_material_points=wallSamples,
            architecture=recipe.GetProperty("architecture").GetString(),precooler_tube_count=tubeCount,
            cooling_route_count=cooling.GetProperty("routes").GetArrayLength(),cooling_centerline_samples=coolingSamples,
            cooling_clearance_samples=coolingClearanceSamples,cooling_sampled_clear_diameter_mm=.8f,
            intentional_port_aperture_samples=portApertureSamples,
            precooler_length_mm=hxEnd-hxStart,
            voxel_mm=pitch,zero_area_triangles_removed=degenerateRemoved,
            geometry_pipeline="triangle_mesh_to_voxels_then_implicit_booleans",input_triangle_count=inputTriangles,
            boolean_reference_samples=booleanReferenceSamples,boolean_operations=BooleanCounts,
            libraries=new[]{"PicoGK: IImplicit + voxel booleans", "Vega Geometry: sampled lobed sections",
                "LEAP71 ShapeKernel: BasePipe", "LEAP71 LatticeLibrary: ImplicitModular + RawGyroidTPMSPattern + FullWallLogic",
                "LEAP71 LatticeLibrary: RegularCellArray + BodyCentreLattice"}
        }));
        Console.WriteLine("Native demonstrator exported");
    }
}
