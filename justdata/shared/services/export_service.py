"""
Unified Export Service for NCRC Applications

Provides consistent PDF, Excel, and Image export functionality across all apps.

Version: 1.0.0
Initial release with unified export functionality for PDF, Excel, and Image exports.
"""

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from flask import send_file, request, session

# Try to import structlog, fall back to standard logging if not available
try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ExportService:
    """Unified export service for all NCRC applications"""
    
    def __init__(self, app_name: str):
        """
        Initialize export service
        
        Args:
            app_name: Name of the application (e.g., 'BizSight', 'LendSight')
        """
        self.app_name = app_name
        self.logo_path = self._find_ncrc_logo()
    
    def _find_ncrc_logo(self) -> Optional[str]:
        """
        Find NCRC logo file in common locations
        
        Returns:
            Path to logo file if found, None otherwise
        """
        logo_filenames = [
            "ncrc-logo.png",
            "ncrc-logo.jpg",
            "NCRC color FINAL.jpg",
            "NCRC_Logo.png",
            "NCRC_Logo.jpg"
        ]
        
        # Possible locations
        base_paths = [
            Path(__file__).parent.parent.parent,  # Project root
            Path(__file__).parent.parent.parent.parent,  # Dream root
        ]
        
        # Check in static/img directories
        for base_path in base_paths:
            for app_dir in ['bizsight', 'lendsight']:
                for logo_name in logo_filenames:
                    logo_path = base_path / 'apps' / app_dir / 'static' / 'img' / logo_name
                    if logo_path.exists():
                        return str(logo_path)
            
            # Check resources folder
            for logo_name in logo_filenames:
                logo_path = base_path / 'resources' / logo_name
                if logo_path.exists():
                    return str(logo_path)
        
        logger.warning("NCRC logo not found in standard locations")
        return None
    
    def export_to_pdf(
        self,
        report_data: Dict[str, Any],
        metadata: Dict[str, Any],
        job_id: Optional[str] = None,
        report_url: Optional[str] = None
    ) -> Any:
        """
        Export report to PDF with magazine-style formatting
        
        Args:
            report_data: Report data dictionary
            metadata: Report metadata (county, state, etc.)
            job_id: Job ID for retrieving full report
            report_url: URL to the report page (if not provided, will be constructed)
            
        Returns:
            Flask response with PDF file
        """
        try:
            from playwright.sync_api import sync_playwright
            
            # Create temporary file for PDF
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(tmp_fd)
            
            # Build report URL if not provided
            if not report_url:
                base_url = request.url_root.rstrip('/')
                report_url = f"{base_url}/report"
                if job_id:
                    report_url += f"?job_id={job_id}"
            
            # Use Playwright to render the page
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to report page
                page.goto(report_url, wait_until='networkidle', timeout=60000)
                
                # Wait for report content
                page.wait_for_selector('#reportContent', state='visible', timeout=30000)
                page.wait_for_timeout(2000)  # Wait for tables to populate
                
                # Generate PDF with magazine-style formatting
                # Minimal margins for maximum content, professional layout
                page.pdf(
                    path=tmp_path,
                    format='Letter',
                    margin={
                        'top': '0.4in',      # Minimal top margin
                        'right': '0.4in',    # Minimal right margin
                        'bottom': '0.6in',   # Space for footer/page numbers
                        'left': '0.4in'      # Minimal left margin
                    },
                    print_background=True,
                    display_header_footer=True,
                    header_template=self._get_pdf_header_template(),
                    footer_template=self._get_pdf_footer_template(),
                    prefer_css_page_size=True,
                    scale=0.98  # Slight scale to ensure content fits
                )
                
                browser.close()
            
            # Generate filename
            filename = self._generate_filename(metadata, '.pdf')
            
            # Send file and schedule cleanup
            response = send_file(
                tmp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
            
            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except:
                    pass
            
            return response
            
        except Exception as e:
            logger.error("PDF export failed", error=str(e), app=self.app_name)
            raise
    
    def _get_pdf_header_template(self) -> str:
        """Get PDF header template with NCRC branding"""
        logo_html = ""
        if self.logo_path and os.path.exists(self.logo_path):
            # Logo would be embedded in header, but Playwright header templates are limited
            # Logo will be in the HTML content itself
            pass
        
        return '<div style="height: 0.3in;"></div>'  # Minimal header space
    
    def _get_pdf_footer_template(self) -> str:
        """Get PDF footer template with page numbers and branding"""
        return f'''
        <div style="font-size: 9pt; color: #666; text-align: center; width: 100%; 
                     font-family: Inter, Arial, sans-serif; padding-top: 5px;">
            <span class="pageNumber"></span> / <span class="totalPages"></span> | 
            NCRC {self.app_name} Report
        </div>
        '''
    
    def export_to_excel(
        self,
        report_data: Dict[str, Any],
        metadata: Dict[str, Any],
        excel_export_func: callable
    ) -> Any:
        """
        Export report to Excel using provided export function
        
        Args:
            report_data: Report data dictionary
            metadata: Report metadata
            excel_export_func: Function that handles Excel export (app-specific)
            
        Returns:
            Flask response with Excel file
        """
        try:
            import tempfile
            
            # Create temporary file
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
            os.close(tmp_fd)
            
            # Call app-specific Excel export function
            excel_export_func(report_data, tmp_path, metadata=metadata)
            
            # Generate filename
            filename = self._generate_filename(metadata, '.xlsx')
            
            # Send file and schedule cleanup
            response = send_file(
                tmp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except:
                    pass
            
            return response
            
        except Exception as e:
            logger.error("Excel export failed", error=str(e), app=self.app_name)
            raise
    
    def export_to_images(
        self,
        report_data: Dict[str, Any],
        metadata: Dict[str, Any],
        job_id: Optional[str] = None,
        report_url: Optional[str] = None,
        elements: Optional[List[str]] = None
    ) -> Any:
        """
        Export report tables/charts as presentation-ready images
        
        Args:
            report_data: Report data dictionary
            metadata: Report metadata
            job_id: Job ID for retrieving full report
            report_url: URL to the report page
            elements: List of element IDs/selectors to export (if None, exports all tables/charts)
            
        Returns:
            Flask response with ZIP file containing images
        """
        try:
            from playwright.sync_api import sync_playwright
            from PIL import Image as PILImage
            import io
            
            # Create temporary directory for images
            tmp_dir = tempfile.mkdtemp()
            images_created = []
            
            # Build report URL if not provided
            if not report_url:
                base_url = request.url_root.rstrip('/')
                report_url = f"{base_url}/report"
                if job_id:
                    report_url += f"?job_id={job_id}"
            
            # Use Playwright to capture elements
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to report page
                page.goto(report_url, wait_until='networkidle', timeout=60000)
                page.wait_for_selector('#reportContent', state='visible', timeout=30000)
                page.wait_for_timeout(2000)
                
                # Find all tables and charts if elements not specified
                if not elements:
                    elements = self._find_exportable_elements(page)
                
                # Export each element as image
                for i, element_selector in enumerate(elements):
                    try:
                        # Wait for element to be visible
                        try:
                            page.wait_for_selector(element_selector, state='visible', timeout=5000)
                        except:
                            # Try without state check
                            page.wait_for_selector(element_selector, timeout=5000)
                        
                        # Capture element screenshot
                        element = page.locator(element_selector).first
                        if element.count() > 0:
                            screenshot_bytes = element.screenshot(type='png', scale=2)  # 2x for high DPI
                            
                            # Add NCRC logo to image
                            image_with_logo = self._add_logo_to_image(screenshot_bytes)
                            
                            # Save image
                            safe_name = element_selector.replace('#', '').replace('.', '_').replace(' ', '_')
                            image_filename = f"image_{i+1:02d}_{safe_name}.png"
                            image_path = os.path.join(tmp_dir, image_filename)
                            with open(image_path, 'wb') as f:
                                f.write(image_with_logo)
                            
                            images_created.append(image_path)
                        
                    except Exception as e:
                        logger.warning(f"Failed to export element {element_selector}", error=str(e))
                        continue
                
                browser.close()
            
            # Create ZIP file
            zip_fd, zip_path = tempfile.mkstemp(suffix='.zip')
            os.close(zip_fd)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for image_path in images_created:
                    zipf.write(image_path, os.path.basename(image_path))
            
            # Cleanup individual images
            for image_path in images_created:
                try:
                    os.unlink(image_path)
                except:
                    pass
            try:
                os.rmdir(tmp_dir)
            except:
                pass
            
            # Generate filename
            filename = self._generate_filename(metadata, '.zip')
            
            # Send file and schedule cleanup
            response = send_file(
                zip_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/zip'
            )
            
            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(zip_path):
                        os.unlink(zip_path)
                except:
                    pass
            
            return response
            
        except Exception as e:
            logger.error("Image export failed", error=str(e), app=self.app_name)
            raise
    
    def _find_exportable_elements(self, page) -> List[str]:
        """Find all exportable tables and charts in the report"""
        elements = []
        
        # Find all tables with IDs or create selectors
        try:
            # Try to find tables by common selectors
            table_selectors = [
                '#topLendersTableNumber',
                '#topLendersTableAmount',
                '#comparisonTableNumber',
                '#comparisonTableAmount',
                '#countySummaryTable',
                'table.data-table',
                'table'
            ]
            
            for selector in table_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        # Check if element is visible
                        if element.is_visible(timeout=1000):
                            elements.append(selector)
                except:
                    continue
            
            # Find charts
            chart_selectors = [
                'canvas',
                'svg.chart',
                '.chart-container',
                '[id*="chart"]'
            ]
            
            for selector in chart_selectors:
                try:
                    elements_found = page.locator(selector).all()
                    for elem in elements_found:
                        elem_id = elem.get_attribute('id')
                        if elem_id:
                            elements.append(f'#{elem_id}')
                except:
                    continue
                    
        except Exception as e:
            logger.warning("Error finding exportable elements", error=str(e))
        
        # If no elements found, return common table selectors as fallback
        if not elements:
            elements = [
                '#topLendersTableNumber',
                '#topLendersTableAmount',
                '#comparisonTableNumber',
                '#comparisonTableAmount'
            ]
        
        return elements
    
    def _add_logo_to_image(self, image_bytes: bytes) -> bytes:
        """
        Add NCRC logo to image (bottom right corner)
        
        Args:
            image_bytes: Original image bytes
            
        Returns:
            Image bytes with logo added
        """
        try:
            try:
                from PIL import Image as PILImage
            except ImportError:
                # PIL not available, return original
                logger.warning("PIL/Pillow not available, skipping logo addition")
                return image_bytes
            
            import io
            
            # Open original image
            img = PILImage.open(io.BytesIO(image_bytes))
            
            # Load logo if available
            if self.logo_path and os.path.exists(self.logo_path):
                try:
                    logo = PILImage.open(self.logo_path)
                    
                    # Resize logo (60px height, maintain aspect ratio)
                    logo_height = 60
                    logo_width = int((logo.width / logo.height) * logo_height)
                    logo = logo.resize((logo_width, logo_height), PILImage.Resampling.LANCZOS)
                    
                    # Convert logo to RGBA if needed
                    if logo.mode != 'RGBA':
                        logo = logo.convert('RGBA')
                    
                    # Apply 90% opacity
                    if logo.mode == 'RGBA':
                        alpha = logo.split()[3]
                        alpha = alpha.point(lambda p: int(p * 0.9))
                        logo.putalpha(alpha)
                    
                    # Calculate position (bottom right, with padding)
                    padding = 10
                    x = img.width - logo_width - padding
                    y = img.height - logo_height - padding
                    
                    # Ensure coordinates are valid
                    if x < 0:
                        x = padding
                    if y < 0:
                        y = padding
                    
                    # Paste logo onto image
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    img.paste(logo, (x, y), logo)
                except Exception as logo_error:
                    logger.warning("Failed to add logo", error=str(logo_error))
            
            # Convert back to bytes
            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.warning("Failed to add logo to image", error=str(e))
            # Return original image if logo addition fails
            return image_bytes
    
    def _generate_filename(self, metadata: Dict[str, Any], extension: str) -> str:
        """
        Generate consistent filename for exports
        
        Args:
            metadata: Report metadata
            extension: File extension (e.g., '.pdf', '.xlsx')
            
        Returns:
            Generated filename
        """
        import re
        from datetime import datetime
        
        # Get county and state from metadata
        counties = metadata.get('counties', [])
        if counties and len(counties) > 0:
            first_county = counties[0]
            if ',' in first_county:
                county_name, state_name = [part.strip() for part in first_county.rsplit(',', 1)]
            else:
                county_name = first_county
                state_name = ''
        else:
            county_name = ''
            state_name = ''
        
        # Clean names for filename
        def clean_name(name):
            name = re.sub(r'\s+County\s*$', '', name, flags=re.IGNORECASE)
            name = name.replace(',', '')
            name = re.sub(r'[^\w\s-]', '', name)
            name = re.sub(r'[\s-]+', '_', name)
            return name
        
        county_clean = clean_name(county_name)
        state_clean = clean_name(state_name) if state_name else ''
        
        # Build filename: NCRC_[AppName]_[County]_[State]_[timestamp]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        app_clean = self.app_name.replace(' ', '_')
        
        if state_clean:
            filename = f'NCRC_{app_clean}_{county_clean}_{state_clean}_{timestamp}{extension}'
        elif county_clean:
            filename = f'NCRC_{app_clean}_{county_clean}_{timestamp}{extension}'
        else:
            filename = f'NCRC_{app_clean}_Report_{timestamp}{extension}'
        
        # Clean up
        filename = re.sub(r'__+', '_', filename)
        
        return filename
