
using System.CommandLine;

namespace PalUE4Exporter;

internal class Program
{


    public static async Task<int> Main(string[] args)
    {
        var archiveOption = new Option<DirectoryInfo>(
            "--archive",
            "-a")
        {
            Description = "Path to the Palworld Paks directory.",
            Required = true
        };

        var mappingsOption = new Option<FileInfo>(
            "--mappings",
            "-m")
        {
            Description = "Path to the .usmap mappings file.",
            Required = true
        };

        var outputOption = new Option<DirectoryInfo>(
            "--output",
            "-o")
        {
            Description = "Directory where exported files are written.",
            Required = true
        };

        var prefixOption = new Option<string>(
            "--prefix",
            "-p")
        {
            Description = "Package path prefix to export.",
            Required = true
        };

        var debugOption = new Option<bool>(
            "--debug")
        {
            Description = "Enable debug output."
        };

        var root = new RootCommand(
            "Palworld UE4 asset exporter.");

        root.Options.Add(archiveOption);
        root.Options.Add(mappingsOption);
        root.Options.Add(outputOption);
        root.Options.Add(prefixOption);
        root.Options.Add(debugOption);

        root.SetAction(async parseResult =>
        {
            var archive = parseResult.GetValue(archiveOption)!;
            var mappings = parseResult.GetValue(mappingsOption)!;
            var output = parseResult.GetValue(outputOption)!;
            var prefix = parseResult.GetValue(prefixOption)!;
            var debug = parseResult.GetValue(debugOption);

            var exporter = new AssetExporter();

            var progress = new Progress<ExportProgress>(
                p =>
                {
                    var text = $"[{p.Current}/{p.Total}] {p.Path}";

                    try
                    {
                        var width = Console.WindowWidth;

                        // Leave one character margin so we don't wrap.
                        if (text.Length >= width)
                            text = text[..(width - 1)];

                        Console.Write("\r" + text.PadRight(width - 1));
                    }
                    catch
                    {
                        // Fallback for redirected/non-interactive output.
                        Console.Write("\r" + text);
                    }

                    if (p.Error is not null)
                    {
                        Console.WriteLine();
                        Console.Error.WriteLine(
                            $"ERROR: {p.Path}: {p.Error}");
                    }
                });

            Console.WriteLine("Starting export...");
            Console.WriteLine("Starting export...");
            Console.WriteLine($"  Archive:  {archive.FullName}");
            Console.WriteLine($"  Mappings: {mappings.FullName}");
            Console.WriteLine($"  Output:   {output.FullName}");
            Console.WriteLine($"  Debug:    {debug}");
            Console.WriteLine($"  Prefix:   {prefix}");

            Console.WriteLine();

            var result = await exporter.RunAsync(
                new ExportOptions(
                    archive.FullName,
                    mappings.FullName,
                    output.FullName,
                        [prefix],
                    debug),
                progress);

            Console.WriteLine();
            Console.WriteLine();
            Console.WriteLine(
                $"Processed: {result.Processed}");

            Console.WriteLine(
                $"Failed:    {result.Failed}");

            return result.Failed == 0 ? 0 : 1;
        });

        return await root.Parse(args).InvokeAsync();
    }

    private static Dictionary<string, string> ParseArgs(string[] rawArgs)
    {
        var map = new Dictionary<string, string>(
            StringComparer.OrdinalIgnoreCase);

        for (var i = 0; i < rawArgs.Length; i++)
        {
            if (!rawArgs[i].StartsWith("--"))
                continue;

            var key = rawArgs[i][2..];

            if (i + 1 < rawArgs.Length &&
                !rawArgs[i + 1].StartsWith("--"))
            {
                map[key] = rawArgs[++i];
            }
            else
            {
                map[key] = "true";
            }
        }

        return map;
    }

    private static void DrawProgressBar(
        int current,
        int totalCount,
        int failedCount,
        string path)
    {
        const int barWidth = 40;

        var pct = totalCount == 0
            ? 1.0
            : (double)current / totalCount;

        var filled = (int)(barWidth * pct);

        var bar =
            new string('#', filled) +
            new string('-', barWidth - filled);

        var prefix =
            $"[{bar}] {current}/{totalCount} ({pct:P0})  Failed: {failedCount}   ";

        int windowWidth;

        try
        {
            windowWidth = Console.WindowWidth;
        }
        catch
        {
            windowWidth = 120;
        }

        var available =
            Math.Max(10, windowWidth - prefix.Length - 1);

        var displayPath =
            path.Length > available
                ? "..." + path[^(available - 3)..]
                : path.PadRight(available);

        Console.Write($"\r{prefix}{displayPath}");
    }
}