
def get_dark_layout(title='', xaxis_title='', yaxis_title='', height=400):
    """Returns a standardized dark theme layout for Plotly charts"""
    return {
        'title': dict(text=title, font=dict(color='#ffffff', size=20)),
        'xaxis': dict(
            title=dict(text=xaxis_title, font=dict(color='#ffffff', size=14)),
            tickfont=dict(color='#ffffff', size=12),
            gridcolor='rgba(255, 255, 255, 0.1)',
            showgrid=True,
            zeroline=False
        ),
        'yaxis': dict(
            title=dict(text=yaxis_title, font=dict(color='#ffffff', size=14)),
            tickfont=dict(color='#ffffff', size=12),
            gridcolor='rgba(255, 255, 255, 0.1)',
            showgrid=True,
            zeroline=False
        ),
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        'font': dict(color='#ffffff'),
        'hoverlabel': dict(bgcolor='rgba(15, 12, 41, 0.9)', font=dict(color='#ffffff')),
        'legend': dict(font=dict(color='#ffffff', size=12)),
        'height': height,
        'margin': dict(l=60, r=40, t=50, b=50)
    }
