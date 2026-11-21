using System.Text.Json;
try
{
    if(args.Length==4 && args[0]=="probe-assembly")
    {
        using var config=JsonDocument.Parse(File.ReadAllText(args[1]));
        Demonstrator.ProbeAssembly(config.RootElement,args[2]);return;
    }
    if(args.Length==4 && args[0]=="routing-grid")
    {
        using var config=JsonDocument.Parse(File.ReadAllText(args[1]));
        Demonstrator.RoutingGrid(config.RootElement,args[2]);return;
    }
    if(args.Length==4 && (args[0]=="bell-cooling"||args[0]=="cooling-detail"))
    {
        using var coolingInput=JsonDocument.Parse(File.ReadAllText(args[1]));
        if(args[0]=="bell-cooling" && args[3]=="0.1")Demonstrator.Cooling(coolingInput.RootElement,args[2]);
        else if(args[0]=="cooling-detail" && args[3]=="0.009")Demonstrator.CoolingDetail(coolingInput.RootElement,args[2]);
        else throw new ArgumentException("Invalid cooling voxel pitch");
        return;
    }
    if(args.Length==4 && args[0]=="integrate")
    {
        if(args[3]!="0.1")throw new ArgumentException("Integration requires 0.1 mm voxels");
        using var integrationInput=JsonDocument.Parse(File.ReadAllText(args[1]));
        Demonstrator.Integrate(integrationInput.RootElement,args[2]);
        return;
    }
    if(args.Length==4 && args[0]=="architecture")
    {
        if(args[3]!="0.1")throw new ArgumentException("Architecture components require 0.1 mm voxels");
        using var architectureInput=JsonDocument.Parse(File.ReadAllText(args[1]));
        Demonstrator.Architecture(architectureInput.RootElement,args[2]);
        return;
    }
    if(args.Length==4 && args[0]=="detail")
    {
        if(args[3]!="0.01")throw new ArgumentException("Detail pitch must be 0.01 mm");
        using var detailInput=JsonDocument.Parse(File.ReadAllText(args[1]));
        Demonstrator.Detail(detailInput.RootElement,args[2]);
        return;
    }
    if(args.Length!=4 || args[0]!="demonstrator")
        throw new ArgumentException("Usage: Vega.Native demonstrator <recipe.json> <output-folder> <voxel-mm>");
    float pitch=float.Parse(args[3],System.Globalization.CultureInfo.InvariantCulture);
    if(!float.IsFinite(pitch)||(pitch!=.2f && pitch!=.3f && pitch!=.4f && pitch!=.7f))
        throw new ArgumentException("Supported voxel pitches are 0.2, 0.3, 0.4 and 0.7 mm");
    using var input=JsonDocument.Parse(File.ReadAllText(args[1]));
    if(input.RootElement.GetProperty("voxel_mm").GetSingle()!=pitch)
        throw new ArgumentException("Recipe and native voxel pitch differ");
    Demonstrator.Build(input.RootElement,args[2],pitch);
}
catch(Exception error)
{
    Console.Error.WriteLine(error.ToString());
    Environment.ExitCode=1;
}
