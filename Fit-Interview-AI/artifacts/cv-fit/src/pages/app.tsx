import { useState } from "react";
import { useLocation } from "wouter";
import { useAnalyzeCV } from "@workspace/api-client-react";
import { extractTextFromPDF } from "@/lib/pdf-parser";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { UploadCloud, FileText, Briefcase, ChevronRight, Loader2 } from "lucide-react";

export default function Home() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const analyzeCV = useAnalyzeCV();
  
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type !== "application/pdf") {
        toast({
          title: "Invalid file format",
          description: "Please upload a PDF file.",
          variant: "destructive"
        });
        return;
      }
      setCvFile(file);
    }
  };

  const handleAnalyze = async () => {
    if (!cvFile || !jdText) {
      toast({
        title: "Missing information",
        description: "Please provide both your CV (PDF) and the Job Description.",
        variant: "destructive"
      });
      return;
    }

    try {
      setIsProcessing(true);
      
      // Extract text
      const cvText = await extractTextFromPDF(cvFile);
      
      // Send to API
      analyzeCV.mutate({
        data: {
          cv_text: cvText,
          jd_text: jdText
        }
      }, {
        onSuccess: (result) => {
          sessionStorage.setItem("analysisResult", JSON.stringify(result));
          sessionStorage.setItem("cv_text", cvText);
          sessionStorage.setItem("jd_text", jdText);
          setLocation("/results");
        },
        onError: (error) => {
          toast({
            title: "Analysis Failed",
            description: "There was an error analyzing your CV. Please try again.",
            variant: "destructive"
          });
          setIsProcessing(false);
        }
      });
      
    } catch (error) {
      toast({
        title: "PDF Parsing Error",
        description: "Failed to read the PDF file. Please ensure it's a valid text-based PDF.",
        variant: "destructive"
      });
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <div className="flex-1 max-w-5xl w-full mx-auto p-6 flex flex-col justify-center">
        <div className="mb-10 text-center space-y-4">
          <div className="inline-flex items-center justify-center p-3 bg-emerald-100 rounded-2xl mb-4">
            <Briefcase className="w-8 h-8 text-emerald-600" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900">
            Hack Your Next Job Interview
          </h1>
          <p className="text-lg text-slate-500 max-w-2xl mx-auto">
            Upload your CV and the target job description. We'll analyze the fit, highlight missing skills, and prepare a tailored resume with an interactive mock interview.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 items-start">
          <Card className="border-slate-200 shadow-sm rounded-xl overflow-hidden">
            <CardHeader className="bg-white border-b border-slate-100 pb-4">
              <CardTitle className="flex items-center gap-2 text-xl">
                <FileText className="w-5 h-5 text-emerald-600" />
                1. Upload CV
              </CardTitle>
              <CardDescription>Upload your current resume in PDF format</CardDescription>
            </CardHeader>
            <CardContent className="p-6 bg-white">
              <label 
                className={`flex flex-col items-center justify-center w-full h-48 border-2 border-dashed rounded-xl cursor-pointer transition-colors ${
                  cvFile ? 'border-emerald-500 bg-emerald-50' : 'border-slate-300 hover:bg-slate-50 hover:border-emerald-400 bg-slate-50/50'
                }`}
              >
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  {cvFile ? (
                    <>
                      <FileText className="w-10 h-10 text-emerald-500 mb-3" />
                      <p className="mb-2 text-sm font-semibold text-slate-900">{cvFile.name}</p>
                      <p className="text-xs text-slate-500">Click to change file</p>
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-10 h-10 text-slate-400 mb-3" />
                      <p className="mb-2 text-sm text-slate-600 font-medium">
                        <span className="font-semibold text-emerald-600">Click to upload</span> or drag and drop
                      </p>
                      <p className="text-xs text-slate-500">PDF (Max 5MB)</p>
                    </>
                  )}
                </div>
                <input 
                  type="file" 
                  className="hidden" 
                  accept="application/pdf"
                  onChange={handleFileChange}
                />
              </label>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm rounded-xl overflow-hidden">
            <CardHeader className="bg-white border-b border-slate-100 pb-4">
              <CardTitle className="flex items-center gap-2 text-xl">
                <Briefcase className="w-5 h-5 text-emerald-600" />
                2. Job Description
              </CardTitle>
              <CardDescription>Paste the description of the role you want</CardDescription>
            </CardHeader>
            <CardContent className="p-6 bg-white">
              <Textarea 
                placeholder="Paste the full job description here..."
                className="min-h-[192px] resize-none focus-visible:ring-emerald-500 border-slate-200"
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
              />
            </CardContent>
          </Card>
        </div>

        <div className="mt-10 flex justify-center">
          <Button 
            size="lg" 
            className="w-full md:w-auto px-12 py-6 text-lg rounded-xl bg-slate-900 hover:bg-slate-800 text-white shadow-lg hover:shadow-xl transition-all"
            onClick={handleAnalyze}
            disabled={isProcessing || !cvFile || !jdText}
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-6 h-6 mr-2 animate-spin" />
                Analyzing Fit...
              </>
            ) : (
              <>
                Analyze Match
                <ChevronRight className="w-5 h-5 ml-2" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
