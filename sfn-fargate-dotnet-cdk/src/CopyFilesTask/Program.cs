using System.Text.Json;
using WorkflowApp.Models;
namespace CopyFilesTask
{
    public class Program
    {
        public static void Main(string[] args)
        {

            using (var sw = new StreamWriter(Console.OpenStandardOutput()))
            {
                var input = Environment.GetEnvironmentVariable("Input");
                if (!string.IsNullOrEmpty(input))
                {
                    sw.WriteLine(input);
                    var copyRequest = JsonSerializer.Deserialize<CopyRequest>(input!);
                    sw.AutoFlush = true;
                    sw.WriteLine($"Copy files from {copyRequest?.SourceLocation} to {copyRequest?.TargetLocation} started...");
                    Thread.Sleep(500);
                    sw.WriteLine($"Copy files from {copyRequest?.SourceLocation} to {copyRequest?.TargetLocation} finished...");
                }
                else
                {
                    sw.WriteLine("Input not found.");
                }
            }
        }
    }
}

