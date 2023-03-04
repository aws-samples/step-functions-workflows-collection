using System;
namespace CleanupTask
{
    public class Program
    {
        public static void Main(string[] args)
        {
            var counter = 0;
            var max = -1;
            if (args != null)
            {
                max = args.Length != 0 ? Convert.ToInt32(args[0]) : -1;
                Console.WriteLine(args.Length);
            }
            using (var sw = new StreamWriter(Console.OpenStandardOutput()))
            {
                sw.AutoFlush = true;
                while (max == -1 || counter < max)
                {
                    sw.WriteLine($"**Files cleaned up** {++counter}");
                    Thread.Sleep(TimeSpan.FromMilliseconds(10000));
                }

            }
        }
    }
}

