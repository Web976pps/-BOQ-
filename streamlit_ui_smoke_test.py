#!/usr/bin/env python3
"""
Comprehensive Streamlit UI Smoke Test
Tests the Streamlit application functionality programmatically
"""

import requests
import time
import os
import sys
import json
import subprocess
from pathlib import Path


class StreamlitUITester:
    """Comprehensive Streamlit UI testing class"""
    
    def __init__(self, base_url="http://localhost:8501"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
    
    def log_test(self, test_name, status, details="", error=None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "error": str(error) if error else None,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"   {details}")
        if error:
            print(f"   Error: {error}")
    
    def test_connectivity(self):
        """Test basic connectivity to Streamlit"""
        try:
            response = self.session.get(f"{self.base_url}", timeout=10)
            if response.status_code == 200:
                self.log_test("Connectivity", "PASS", f"HTTP {response.status_code}")
                return True
            else:
                self.log_test("Connectivity", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Connectivity", "FAIL", error=e)
            return False
    
    def test_health_endpoint(self):
        """Test Streamlit health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/healthz", timeout=5)
            if response.status_code == 200 and "ok" in response.text.lower():
                self.log_test("Health Endpoint", "PASS", "Health check OK")
                return True
            else:
                self.log_test("Health Endpoint", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Endpoint", "FAIL", error=e)
            return False
    
    def test_app_loading(self):
        """Test if the Streamlit app loads properly"""
        try:
            response = self.session.get(f"{self.base_url}", timeout=10)
            html_content = response.text
            
            # Check for Streamlit indicators
            indicators = [
                "streamlit",
                "window.streamlitConfig",
                "data-testid",
            ]
            
            found_indicators = [ind for ind in indicators if ind.lower() in html_content.lower()]
            
            if len(found_indicators) >= 2:
                self.log_test("App Loading", "PASS", f"Found {len(found_indicators)} Streamlit indicators")
                return True
            else:
                self.log_test("App Loading", "FAIL", f"Only found {len(found_indicators)} indicators")
                return False
                
        except Exception as e:
            self.log_test("App Loading", "FAIL", error=e)
            return False
    
    def test_enhanced_app_features(self):
        """Test enhanced app specific features by importing and testing components"""
        try:
            # Test if we can import enhanced components
            sys.path.insert(0, '/workspace')
            from enhanced_app import EnhancedZoneExtractor, A1PDFProcessor, GeometricAnalyzer, ZoneMemoryManager
            
            # Test component initialization
            extractor = EnhancedZoneExtractor()
            pdf_processor = A1PDFProcessor()
            geometric_analyzer = GeometricAnalyzer()
            memory_manager = ZoneMemoryManager()
            
            # Test basic functionality
            test_text = "INNOVATION HUB CH15 TB01 CREATE SPACE"
            zones = extractor.detect_all_caps_zones(test_text)
            codes = extractor.detect_furniture_codes(test_text)
            
            details = f"Zones: {len(zones)}, Codes: {len(codes)}, Components initialized"
            self.log_test("Enhanced App Components", "PASS", details)
            return True
            
        except Exception as e:
            self.log_test("Enhanced App Components", "FAIL", error=e)
            return False
    
    def test_file_upload_readiness(self):
        """Test if file upload functionality would work"""
        try:
            # Check if test PDFs exist
            test_files = [
                "architectural_test.pdf",
                "test_zones.pdf",
                "input/sample.pdf"
            ]
            
            existing_files = []
            for file_path in test_files:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    existing_files.append(f"{file_path} ({file_size} bytes)")
            
            if existing_files:
                details = f"Test files available: {', '.join(existing_files)}"
                self.log_test("File Upload Readiness", "PASS", details)
                return True
            else:
                self.log_test("File Upload Readiness", "FAIL", "No test PDF files found")
                return False
                
        except Exception as e:
            self.log_test("File Upload Readiness", "FAIL", error=e)
            return False
    
    def test_streamlit_process(self):
        """Test if Streamlit process is running properly"""
        try:
            # Check for Streamlit process
            result = subprocess.run(
                ["ps", "aux"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            streamlit_processes = [
                line for line in result.stdout.split('\n') 
                if 'streamlit' in line.lower() and 'enhanced_app.py' in line
            ]
            
            if streamlit_processes:
                details = f"Found {len(streamlit_processes)} Streamlit process(es)"
                self.log_test("Streamlit Process", "PASS", details)
                return True
            else:
                self.log_test("Streamlit Process", "FAIL", "No enhanced_app.py Streamlit process found")
                return False
                
        except Exception as e:
            self.log_test("Streamlit Process", "FAIL", error=e)
            return False
    
    def test_response_time(self):
        """Test Streamlit response time"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}", timeout=10)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            if response.status_code == 200 and response_time < 5.0:
                details = f"Response time: {response_time:.2f}s"
                self.log_test("Response Time", "PASS", details)
                return True
            else:
                details = f"Response time: {response_time:.2f}s, Status: {response.status_code}"
                self.log_test("Response Time", "FAIL", details)
                return False
                
        except Exception as e:
            self.log_test("Response Time", "FAIL", error=e)
            return False
    
    def test_static_assets(self):
        """Test if Streamlit static assets are being served"""
        try:
            # Test common Streamlit static paths
            static_paths = [
                "/static/css/bootstrap.min.css",
                "/static/js/bootstrap.bundle.min.js",
                "/_stcore/static"
            ]
            
            accessible_assets = 0
            for path in static_paths:
                try:
                    response = self.session.get(f"{self.base_url}{path}", timeout=3)
                    if response.status_code in [200, 304]:  # OK or Not Modified
                        accessible_assets += 1
                except:
                    pass
            
            if accessible_assets > 0:
                details = f"{accessible_assets}/{len(static_paths)} static assets accessible"
                self.log_test("Static Assets", "PASS", details)
                return True
            else:
                self.log_test("Static Assets", "FAIL", "No static assets accessible")
                return False
                
        except Exception as e:
            self.log_test("Static Assets", "FAIL", error=e)
            return False
    
    def run_comprehensive_test(self):
        """Run all smoke tests"""
        print("🔥 STREAMLIT UI SMOKE TEST")
        print("=" * 60)
        print(f"Testing Streamlit application at: {self.base_url}")
        print()
        
        # Run all tests
        tests = [
            self.test_connectivity,
            self.test_health_endpoint,
            self.test_app_loading,
            self.test_enhanced_app_features,
            self.test_file_upload_readiness,
            self.test_streamlit_process,
            self.test_response_time,
            self.test_static_assets
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_func in tests:
            if test_func():
                passed_tests += 1
            time.sleep(0.5)  # Brief pause between tests
        
        # Summary
        print()
        print("📊 SMOKE TEST SUMMARY")
        print("=" * 60)
        
        pass_rate = (passed_tests / total_tests) * 100
        status_icon = "✅" if pass_rate >= 80 else "⚠️" if pass_rate >= 60 else "❌"
        
        print(f"{status_icon} Tests Passed: {passed_tests}/{total_tests} ({pass_rate:.1f}%)")
        
        if pass_rate >= 80:
            print("🎉 UI SMOKE TEST: PASSED - Streamlit application is operational!")
        elif pass_rate >= 60:
            print("⚠️ UI SMOKE TEST: PARTIAL - Some issues detected")
        else:
            print("❌ UI SMOKE TEST: FAILED - Significant issues found")
        
        print()
        print("🔗 Access the application at: http://localhost:8501")
        print()
        
        return pass_rate >= 80


def main():
    """Main test execution"""
    tester = StreamlitUITester()
    
    # Wait a moment for any startup
    print("⏳ Waiting for Streamlit to be ready...")
    time.sleep(3)
    
    # Run comprehensive test
    success = tester.run_comprehensive_test()
    
    # Generate test report
    timestamp = int(time.time())
    report_file = f"streamlit_ui_smoke_test_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "base_url": tester.base_url,
            "total_tests": len(tester.test_results),
            "passed_tests": len([r for r in tester.test_results if r["status"] == "PASS"]),
            "test_results": tester.test_results
        }, f, indent=2)
    
    print(f"📋 Detailed test report saved to: {report_file}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()