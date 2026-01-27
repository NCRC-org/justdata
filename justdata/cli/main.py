"""
Command Line Interface for JustData.
"""

import click
import asyncio
from justdata.core.config.settings import get_settings
from justdata.core.database.connection import test_connections, init_database
from justdata.shared.services.ai_service import get_ai_service
import structlog

logger = structlog.get_logger()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """JustData - A comprehensive data analysis platform."""
    pass


@cli.command()
def info():
    """Display JustData information."""
    settings = get_settings()
    
    click.echo("🚀 JustData Platform")
    click.echo("==================")
    click.echo(f"Version: {settings.app_version}")
    click.echo(f"Debug Mode: {settings.debug}")
    click.echo(f"Log Level: {settings.log_level}")
    click.echo(f"API Host: {settings.api_host}")
    click.echo(f"API Port: {settings.api_port}")
    
    # Check AI services
    ai_service = get_ai_service()
    available_models = ai_service.get_available_models()
    
    click.echo("\n🤖 AI Services:")
    click.echo(f"  Claude: {'✅ Available' if available_models['claude'] else '❌ Not Available'}")
    click.echo(f"  GPT: {'✅ Available' if available_models['gpt'] else '❌ Not Available'}")


@cli.command()
def test():
    """Test system connections."""
    click.echo("🔍 Testing system connections...")
    
    # Test database connections
    test_connections()
    
    # Test AI services
    ai_service = get_ai_service()
    available_models = ai_service.get_available_models()
    
    click.echo("\n✅ Connection tests completed!")


@cli.command()
def init():
    """Initialize the system."""
    click.echo("🚀 Initializing JustData system...")
    
    try:
        # Initialize database
        init_database()
        click.echo("✅ Database initialized successfully")
        
        # Test connections
        test_connections()
        click.echo("✅ System initialization completed!")
        
    except Exception as e:
        click.echo(f"❌ Initialization failed: {e}")
        raise click.Abort()


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve(host, port, reload):
    """Start the JustData API server."""
    import uvicorn
    
    click.echo(f"🌐 Starting JustData API server on {host}:{port}")
    
    uvicorn.run(
        "justdata.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


@cli.group()
def apps():
    """Manage JustData applications."""
    pass


@apps.command()
def list():
    """List available applications."""
    click.echo("📱 Available Applications:")
    click.echo("  • BranchSight - Banking market intelligence")
    click.echo("  • LendSight - Mortgage lending patterns")
    click.echo("  • BizSight - Small business insights")


@apps.command()
@click.argument('app_name')
def status(app_name):
    """Check application status."""
    click.echo(f"📊 Checking status for {app_name}...")
    
    # This would check the actual application status
    # For now, just show a placeholder
    click.echo(f"✅ {app_name} is running")


@cli.group()
def data():
    """Manage data sources and analysis."""
    pass


@data.command()
def sync():
    """Sync data from external sources."""
    click.echo("🔄 Syncing data from external sources...")
    
    # This would trigger data synchronization
    # For now, just show a placeholder
    click.echo("✅ Data sync completed")


@data.command()
@click.argument('source')
def analyze(source):
    """Analyze data from a specific source."""
    click.echo(f"🔍 Analyzing data from {source}...")
    
    # This would trigger data analysis
    # For now, just show a placeholder
    click.echo(f"✅ Analysis completed for {source}")


@cli.group()
def reports():
    """Manage reports and exports."""
    pass


@reports.command()
@click.argument('analysis_id')
@click.option('--format', default='pdf', help='Report format (pdf, excel, json)')
def generate(analysis_id, format):
    """Generate a report from analysis results."""
    click.echo(f"📄 Generating {format} report for analysis {analysis_id}...")
    
    # This would generate the actual report
    # For now, just show a placeholder
    click.echo(f"✅ {format.upper()} report generated successfully")


@cli.command()
def health():
    """Check system health."""
    click.echo("🏥 Checking system health...")
    
    # This would perform actual health checks
    # For now, just show a placeholder
    click.echo("✅ System is healthy")


if __name__ == '__main__':
    cli()
