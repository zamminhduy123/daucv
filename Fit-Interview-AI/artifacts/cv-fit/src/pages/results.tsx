import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Printer, MessageSquare, ArrowLeft, Briefcase, GraduationCap, CheckCircle2 } from "lucide-react";
import type { CVAnalysisResult } from "@workspace/api-client-react";

export default function Results() {
  const [location, setLocation] = useLocation();
  const [result, setResult] = useState<CVAnalysisResult | null>(null);

  useEffect(() => {
    const data = sessionStorage.getItem("analysisResult");
    if (!data) {
      setLocation("/app");
      return;
    }
    setResult(JSON.parse(data));
  }, [setLocation]);

  if (!result) return null;

  const { match_score, missing_skills, tailored_cv } = result;

  // SVG Progress animation calculations
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (match_score / 100) * circumference;

  let scoreColor = "text-emerald-500";
  let strokeColor = "stroke-emerald-500";
  if (match_score < 50) {
    scoreColor = "text-red-500";
    strokeColor = "stroke-red-500";
  } else if (match_score < 75) {
    scoreColor = "text-amber-500";
    strokeColor = "stroke-amber-500";
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Button variant="ghost" onClick={() => setLocation("/app")} className="text-slate-500 hover:text-slate-900 -ml-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Start Over
          </Button>
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={() => window.print()} className="border-slate-300 text-slate-700">
              <Printer className="w-4 h-4 mr-2" />
              Print / Export CV
            </Button>
            <Button onClick={() => setLocation("/interview")} className="bg-emerald-600 hover:bg-emerald-700 text-white">
              <MessageSquare className="w-4 h-4 mr-2" />
              Start Mock Interview
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6 mt-8 grid lg:grid-cols-[1fr_2fr] gap-8">
        
        {/* Left Column: Analysis */}
        <div className="space-y-6">
          <Card className="border-slate-200 shadow-sm rounded-xl">
            <CardHeader className="pb-2">
              <CardTitle className="text-slate-900">Match Score</CardTitle>
              <CardDescription>Based on CV & Job Description</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center py-6">
              <div className="relative w-48 h-48 flex items-center justify-center">
                {/* Background Circle */}
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 140 140">
                  <circle
                    cx="70"
                    cy="70"
                    r={radius}
                    className="stroke-slate-100"
                    strokeWidth="12"
                    fill="transparent"
                  />
                  {/* Progress Circle */}
                  <circle
                    cx="70"
                    cy="70"
                    r={radius}
                    className={`${strokeColor} transition-all duration-1000 ease-out`}
                    strokeWidth="12"
                    fill="transparent"
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className={`text-5xl font-bold tracking-tighter ${scoreColor}`}>
                    {match_score}%
                  </span>
                  <span className="text-sm font-medium text-slate-500 mt-1">Match</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm rounded-xl">
            <CardHeader className="pb-3">
              <CardTitle className="text-slate-900 flex items-center gap-2">
                Missing Skills
              </CardTitle>
              <CardDescription>Areas to brush up on before interviewing</CardDescription>
            </CardHeader>
            <CardContent>
              {missing_skills.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {missing_skills.map((skill, i) => (
                    <Badge key={i} variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 px-3 py-1 text-sm font-medium">
                      {skill}
                    </Badge>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-2 text-emerald-600 bg-emerald-50 p-4 rounded-lg">
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="font-medium">Perfect match! No missing skills detected.</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Tailored CV Preview */}
        <Card id="cv-preview" className="border-slate-200 shadow-sm rounded-xl overflow-hidden bg-white">
          <CardHeader className="bg-slate-50 border-b border-slate-100 print:hidden">
            <CardTitle className="text-slate-900">Tailored CV Preview</CardTitle>
            <CardDescription>Optimized for the target role</CardDescription>
          </CardHeader>
          <CardContent className="p-8 lg:p-12 prose prose-slate max-w-none">
            
            <div className="text-center mb-10 pb-6 border-b border-slate-200">
              <h1 className="text-4xl font-bold text-slate-900 mb-2 mt-0">{tailored_cv.name}</h1>
            </div>

            <div className="mb-8">
              <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wider mb-3">Professional Summary</h2>
              <p className="text-slate-700 leading-relaxed">
                {tailored_cv.summary}
              </p>
            </div>

            <div className="mb-8">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider mb-4">
                <Briefcase className="w-5 h-5 print:hidden" />
                Experience
              </h2>
              <div className="space-y-6">
                {tailored_cv.experience.map((exp, idx) => (
                  <div key={idx}>
                    <div className="flex justify-between items-baseline mb-2">
                      <h3 className="text-lg font-bold text-slate-900 my-0">{exp.role}</h3>
                      <span className="text-slate-600 font-medium">{exp.company}</span>
                    </div>
                    <ul className="list-disc pl-5 text-slate-700 space-y-1">
                      {exp.bullet_points.map((bullet, bIdx) => (
                        <li key={bIdx}>{bullet}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider mb-3">
                <GraduationCap className="w-5 h-5 print:hidden" />
                Education
              </h2>
              <p className="text-slate-700 font-medium">
                {tailored_cv.education}
              </p>
            </div>

            <div>
              <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wider mb-3">
                Skills
              </h2>
              <div className="flex flex-wrap gap-x-2 gap-y-1">
                {tailored_cv.skills.map((skill, idx) => (
                  <span key={idx} className="text-slate-700">
                    {skill}{idx < tailored_cv.skills.length - 1 ? " • " : ""}
                  </span>
                ))}
              </div>
            </div>

          </CardContent>
        </Card>

      </main>
    </div>
  );
}
