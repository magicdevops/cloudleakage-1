#!/usr/bin/env python3
"""
Terraform AI Analyzer Service - Google Gemini Integration
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

@dataclass
class TerraformAnalysisResult:
    success: bool
    findings: List[Dict[str, Any]]
    security_suggestions: List[Dict[str, Any]]
    cost_suggestions: List[Dict[str, Any]]
    mermaid_diagram: str
    raw_response: str
    error: Optional[str] = None

class TerraformAIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai
                logger.info("Gemini AI initialized")
            except Exception as e:
                logger.error(f"Gemini init failed: {e}")
                self.client = None
        else:
            self.client = None
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def analyze_terraform_state(self, state_data: Dict[str, Any]) -> TerraformAnalysisResult:
        if not self.is_available():
            return self._get_sample_analysis()
        
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(state_data, f, indent=2)
                temp_path = f.name
            
            # Upload and analyze
            uploaded_file = genai.upload_file(path=temp_path, display_name="terraform.json")
            
            prompt = """Analyze this Terraform state file. Return JSON with:
{
  "findings": [{"title": "Resource Found", "description": "Details", "resource_type": "aws_vpc"}],
  "security_suggestions": [{"priority": "high", "title": "Issue", "recommendation": "Fix"}],
  "cost_suggestions": [{"priority": "medium", "title": "Optimization", "potential_savings": "$50/month"}],
  "mermaid_diagram": "graph TD\\nA[VPC] --> B[Subnet]"
}"""
            
            # Try different model names for compatibility
            model_names = ['gemini-1.5-flash', 'gemini-pro', 'gemini-1.0-pro', 'text-bison-001']
            model = None
            for model_name in model_names:
                try:
                    model = genai.GenerativeModel(model_name)
                    break
                except:
                    continue
            
            if not model:
                raise Exception("No compatible Gemini model found")
            response = model.generate_content([prompt, uploaded_file])
            
            # Cleanup
            genai.delete_file(uploaded_file.name)
            os.unlink(temp_path)
            
            return self._parse_response(response.text)
            
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return TerraformAnalysisResult(
                success=False, findings=[], security_suggestions=[], 
                cost_suggestions=[], mermaid_diagram="", raw_response="", error=str(e)
            )
    
    def _parse_response(self, text: str) -> TerraformAnalysisResult:
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = json.loads(text)
            
            return TerraformAnalysisResult(
                success=True,
                findings=data.get('findings', []),
                security_suggestions=data.get('security_suggestions', []),
                cost_suggestions=data.get('cost_suggestions', []),
                mermaid_diagram=data.get('mermaid_diagram', ''),
                raw_response=text
            )
        except Exception as e:
            return TerraformAnalysisResult(
                success=True, findings=[{"title": "AI Response", "description": text[:200]}],
                security_suggestions=[], cost_suggestions=[], mermaid_diagram="", raw_response=text
            )
    
    def _get_sample_analysis(self) -> TerraformAnalysisResult:
        return TerraformAnalysisResult(
            success=True,
            findings=[{"title": "Sample VPC", "description": "Demo analysis", "resource_type": "aws_vpc"}],
            security_suggestions=[{"priority": "high", "title": "Set GEMINI_API_KEY", "recommendation": "Configure API key for AI analysis"}],
            cost_suggestions=[{"priority": "low", "title": "Enable AI", "potential_savings": "Get real suggestions with API key"}],
            mermaid_diagram="graph TD\nA[Configure API] --> B[Get Analysis]",
            raw_response="Sample response - configure GEMINI_API_KEY for real AI analysis"
        )
