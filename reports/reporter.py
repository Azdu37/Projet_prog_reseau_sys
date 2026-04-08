import datetime
import os


def generate_report(report_type, data, output_file):
    """
    Génère un rapport HTML unifié.
    report_type: 'tournament' ou 'battle'
    data: dictionnaire contenant les données nécessaires
    output_file: chemin du fichier de sortie
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    css = """
    :root {
        --primary: #2c3e50;
        --secondary: #34495e;
        --accent: #3498db;
        --success: #27ae60;
        --danger: #e74c3c;
        --warning: #f1c40f;
        --light: #f8f9fa;
        --dark: #212529;
        --red-team: #e74c3c;
        --blue-team: #3498db;
    }
    body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f0f2f5; color: var(--dark); margin: 0; padding: 0; }
    .container { max-width: 1300px; margin: 30px auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
    
    header { border-bottom: 3px solid var(--accent); margin-bottom: 30px; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: flex-end; }
    h1 { color: var(--primary); margin: 0; font-size: 2.5em; }
    .timestamp { color: #666; font-style: italic; }
    
    h2 { color: var(--secondary); border-left: 5px solid var(--accent); padding-left: 15px; margin-top: 40px; }
    
    table { width: 100%; border-collapse: collapse; margin-bottom: 30px; overflow: hidden; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.05); }
    th, td { padding: 12px 15px; text-align: center; border: 1px solid #e1e4e8; }
    th { background-color: var(--primary); color: white; font-weight: 600; text-transform: uppercase; font-size: 0.9em; letter-spacing: 0.5px; }
    tr:nth-child(even) { background-color: #f9fbff; }
    tr:hover { background-color: #f1f4f8; transition: 0.2s; }
    
    .matrix-table th { background-color: var(--secondary); }
    .matrix-table th:first-child { background-color: var(--primary); }
    .diagonal { background-color: #e9ecef; color: #adb5bd; }
    .win-dominant { background-color: #d4edda; color: #155724; }
    .loss-dominant { background-color: #f8d7da; color: #721c24; }
    
    .rank-1 { background-color: #fff9c4 !important; font-weight: bold; }
    .rank-2 { background-color: #f5f5f5 !important; }
    .rank-3 { background-color: #fff3e0 !important; }
    
    .progress-bg { background: #e9ecef; border-radius: 10px; width: 80px; height: 12px; display: inline-block; vertical-align: middle; margin-right: 10px; }
    .progress-fill { height: 100%; border-radius: 10px; }
    .progress-fill.win { background-color: var(--success); }
    .progress-fill.hp { background-color: var(--success); }
    
    .stats-summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
    .stat-card { background: var(--light); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #e1e4e8; }
    .stat-label { font-size: 0.9em; color: #666; text-transform: uppercase; margin-bottom: 5px; }
    .stat-value { font-size: 1.8em; font-weight: bold; color: var(--primary); }
    
    .winner-red { color: var(--danger); font-weight: bold; }
    .winner-blue { color: var(--accent); font-weight: bold; }
    .winner-draw { color: #7f8c8d; }
    .match-error { background-color: #fdecea !important; }
    
    .team-card { padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 20px; }
    .team-R { border-left: 10px solid var(--red-team); background-color: #fff5f5; }
    .team-B { border-left: 10px solid var(--blue-team); background-color: #f5faff; }
    
    .status-alive { color: var(--success); font-weight: bold; }
    .status-dead { color: var(--danger); font-weight: bold; }
    
    #statsTable th, #detailTable th, #unitsTable th {
        cursor: pointer;
        user-select: none;
        position: relative;
        padding-right: 20px;
    }
    #statsTable th:hover, #detailTable th:hover, #unitsTable th:hover {
        background-color: var(--secondary);
    }
    
    th[data-order="asc"]::after { content: ' \\25B2'; position: absolute; right: 5px; }
    th[data-order="desc"]::after { content: ' \\25BC'; position: absolute; right: 5px; }
    
    .export-info { background: #e7f3fe; padding: 15px; border-radius: 8px; border-left: 5px solid var(--accent); margin-bottom: 20px; font-size: 0.95em; }
    .header-info { display: flex; justify-content: space-between; flex-wrap: wrap; background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    .header-info div { margin: 5px 20px; }
    .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    """

    script = """
    function sortTable(tableId, n) {
        const table = document.getElementById(tableId);
        const tbody = table.tBodies[0];
        let rows = Array.from(tbody.rows);
        const header = table.tHead.rows[0].cells[n];
        const currentDir = header.getAttribute('data-order');
        const dir = currentDir === 'asc' ? 'desc' : 'asc';
        
        Array.from(table.tHead.rows[0].cells).forEach(th => th.removeAttribute('data-order'));
        header.setAttribute('data-order', dir);

        rows.sort((rowA, rowB) => {
            const cellA = rowA.cells[n].innerText.trim();
            const cellB = rowB.cells[n].innerText.trim();
            const comparison = cellA.localeCompare(cellB, undefined, { numeric: true, sensitivity: 'base' });
            return dir === 'asc' ? comparison : -comparison;
        });

        for (const row of rows) {
            tbody.appendChild(row);
        }
    }
    """

    if report_type == 'tournament':
        content = _generate_tournament_content(data, now)
        title = "Rapport de Tournoi IA"
    elif report_type == 'battle':
        content = _generate_battle_content(data, now)
        title = f"Rapport de Bataille - Tour {data.get('turn', '?')}"
    elif report_type == 'lanchester':
        content = _generate_lanchester_content(data, now)
        title = f"Rapport Lanchester - {data.get('scenario', 'Bataille')}"
    elif report_type == 'lanchester_plot':
        content = _generate_lanchester_plot_content(data, now)
        title = f"Lois de Lanchester - {data.get('ia1')} vs {data.get('ia2')}"
    else:
        raise ValueError("Type de rapport inconnu")

    # On ajoute Chart.js pour les rapports graphiques
    extra_head = ""
    if report_type in ['lanchester', 'lanchester_plot']:
        extra_head = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>{css}</style>
    {extra_head}
</head>
<body>
    <div class="container">
        {content}
    </div>
    <script>{script}</script>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] Rapport {report_type} généré : {output_file}")


def _generate_tournament_content(data, now):
    # Tableau du classement et stats détaillées par IA
    sorted_ias = sorted(data['generals'], key=lambda x: data['stats_ia'][x]["wins"], reverse=True)
    ranking_rows = ""
    for i, ia in enumerate(sorted_ias):
        s = data['stats_ia'][ia]
        win_rate = (s["wins"] / s["total_matches"] * 100) if s["total_matches"] > 0 else 0
        avg_units = (s["total_units_left"] / s["total_matches"]) if s["total_matches"] > 0 else 0
        avg_time = (s["total_time"] / s["total_matches"]) if s["total_matches"] > 0 else 0
        avg_tps = (s["total_tps"] / s["total_matches"]) if s["total_matches"] > 0 else 0

        rank_class = f"rank-{i + 1}" if i < 3 else ""
        ranking_rows += f"""<tr class="{rank_class}">
            <td>{i + 1}</td>
            <td style="text-align: left; font-weight: bold;">{ia}</td>
            <td>{s['wins']}</td>
            <td>{s['losses']}</td>
            <td>{s['draws']}</td>
            <td><div class="progress-bg"><div class="progress-fill win" style="width: {win_rate}%"></div></div> {win_rate:.1f}%</td>
            <td>{avg_units:.2f}</td>
            <td>{avg_time:.2f}s</td>
            <td>{avg_tps:.1f}</td>
        </tr>"""

    # Construction de la matrice
    matrix_html = "<table class='matrix-table'>"
    matrix_html += "<thead><tr><th>IA 1 (Ligne) \\ IA 2 (Col)</th>"
    for ia in data['generals']:
        matrix_html += f"<th>{ia}</th>"
    matrix_html += "</tr></thead><tbody>"

    for ia1 in data['generals']:
        matrix_html += f"<tr><th>{ia1}</th>"
        for ia2 in data['generals']:
            if ia1 == ia2:
                matrix_html += "<td class='diagonal'>-</td>"
            else:
                results = data['confrontation_matrix'][ia1][ia2]
                total = results["wins"] + results["losses"] + results["draws"]
                win_rate = (results["wins"] / total * 100) if total > 0 else 0
                cell_class = "win-dominant" if win_rate > 50 else (
                    "loss-dominant" if win_rate < 50 and total > 0 else "")
                matrix_html += f"<td class='{cell_class}'>V: {results['wins']}<br>D: {results['losses']}<br>N: {results['draws']}<br><small>({win_rate:.1f}%)</small></td>"
        matrix_html += "</tr>"
    matrix_html += "</tbody></table>"

    # Historique des matches
    detailed_matches_rows = ""
    for match_id in sorted(data['res_dic_brut'].keys()):
        match = data['res_dic_brut'][match_id]
        if not match or "error" in match:
            if match and "error" in match:
                detailed_matches_rows += f"""<tr class="match-error">
                    <td>{match_id}</td><td>-</td><td>{match.get('ia1', '?')}</td><td>{match.get('ia2', '?')}</td>
                    <td colspan="5">ERREUR: {match['error']}</td>
                </tr>"""
            continue
        winner = match['winner_ia']
        winner_class = "winner-red" if winner == match['ia1'] else (
            "winner-blue" if winner == match['ia2'] else "winner-draw")
        detailed_matches_rows += f"""<tr>
            <td>{match_id}</td>
            <td>{match.get('scenario', 'N/A')}</td>
            <td>{match['ia1']}</td>
            <td>{match['ia2']}</td>
            <td class="{winner_class}">{winner}</td>
            <td>{match['turn']}</td>
            <td>{match['units_ia1']} / {match['units_ia2']}</td>
            <td>{match['time_from_start']:.3f}s</td>
            <td>{match.get('real_tps', 0):.1f}</td>
        </tr>"""

    stats_summary = f"""
        <div class="stats-summary-grid">
            <div class="stat-card">
                <div class="stat-label">Total Matchs</div>
                <div class="stat-value">{len(data['res_dic_brut'])}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">TPS Moyen</div>
                <div class="stat-value">{data['stats_summary'].get('real_tps_avg', 0):.1f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Temps Moyen / Match</div>
                <div class="stat-value">{data['stats_summary'].get('time_per_match_avg', 0):.2f}s</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Tours Moyens</div>
                <div class="stat-value">{data['stats_summary'].get('number_turns_avg', 0):.1f}</div>
            </div>
        </div>
    """

    content = f"""
        <header>
            <div>
                <h1>Rapport de Tournoi</h1>
                <div class="timestamp">Généré le {now}</div>
            </div>
            <div style="text-align: right">
                <strong>Total Exécution:</strong> {data['total_execution_time']:.2f}s
            </div>
        </header>
        
        <div class="export-info">
            Ce rapport présente les résultats du tournoi opposant <strong>{len(data['generals'])} IAs</strong> 
            sur <strong>{data['scenarios_count']} scénarios</strong>, avec <strong>{data['matches_per_pair']} match(s)</strong> par paire.
        </div>

        {stats_summary}

        <h2>Classement Général</h2>
        <table id="statsTable"> 
            <thead>
            <tr>
                <th onclick="sortTable('statsTable', 0)">Rang</th>
                <th onclick="sortTable('statsTable', 1)">IA/Général</th>
                <th onclick="sortTable('statsTable', 2)">Victoires</th>
                <th onclick="sortTable('statsTable', 3)">Défaites</th>
                <th onclick="sortTable('statsTable', 4)">Nuls</th>
                <th onclick="sortTable('statsTable', 5)">Taux de Victoire</th>
                <th onclick="sortTable('statsTable', 6)">Unités restantes (moy)</th>
                <th onclick="sortTable('statsTable', 7)">Temps/Match (moy)</th>
                <th onclick="sortTable('statsTable', 8)">TPS (moy)</th>
            </tr>
            </thead>
            <tbody>
                {ranking_rows}
            </tbody>
        </table>

        <h2>Matrice de Confrontation Directe</h2>
        <p>Lecture : IA en ligne (Rouge) contre IA en colonne (Bleue). Résultats vus par l'IA en ligne.</p>
        <div style="overflow-x: auto;">
            {matrix_html}
        </div>

        <h2>Historique Détaillé des Matchs</h2>
        <table id="detailTable"> 
            <thead>
                <tr>
                    <th onclick="sortTable('detailTable',0)">#</th>
                    <th onclick="sortTable('detailTable',1)">Scénario</th>
                    <th onclick="sortTable('detailTable',2)">IA Rouge</th>
                    <th onclick="sortTable('detailTable',3)">IA Bleue</th>
                    <th onclick="sortTable('detailTable',4)">Vainqueur</th>
                    <th onclick="sortTable('detailTable',5)">Tours</th>
                    <th onclick="sortTable('detailTable',6)">Unités (R/B)</th>
                    <th onclick="sortTable('detailTable',7)">Temps</th>
                    <th onclick="sortTable('detailTable',8)">TPS</th>
                </tr>
            </thead>
            <tbody>
                {detailed_matches_rows}
            </tbody>
        </table>
    """
    return content


def _generate_battle_content(data, now):
    teams_content = ""
    for team_code, team_info in data['teams'].items():
        team_name = team_info['name']
        alive = team_info['alive_count']
        total = team_info['total_count']
        dead = total - alive
        hp_percent = team_info['hp_percent']

        type_rows = ""
        for u_type, t_stats in team_info['types'].items():
            type_rows += f"""
                <tr>
                    <td>{u_type}</td>
                    <td>{t_stats['count']}</td>
                    <td>{t_stats['avg_hp']:.1f} ({t_stats['percent']:.1f}%)</td>
                    <td><div class="progress-bg"><div class="progress-fill hp" style="width: {t_stats['percent']}%"></div></div></td>
                </tr>"""

        teams_content += f"""
            <div class="team-card team-{team_code}">
                <h2>Équipe {team_name}</h2>
                <p><strong>Unités en vie:</strong> {alive} / {total} (Pertes: {dead})</p>
                <p><strong>Points de Vie Totaux:</strong> {team_info['total_hp']:.0f} / {team_info['max_hp']:.0f}
                    <div class="progress-bg"><div class="progress-fill hp" style="width: {hp_percent}%"></div></div> {hp_percent:.1f}%
                </p>

                <h3>Détails par Type</h3>
                <table>
                    <tr><th>Type</th><th>Nombre</th><th>HP Moyen</th><th>État</th></tr>
                    {type_rows}
                </table>
            </div>"""

    unit_rows = ""
    for i, u in enumerate(data['units']):
        hp_percent = u['hp_percent']
        status_class = "status-alive" if u['is_alive'] else "status-dead"
        status_text = "VIVANT" if u['is_alive'] else "MORT"
        row_style = "" if u['is_alive'] else "opacity: 0.6;"
        team_color = "var(--red-team)" if u['team_code'] == 'R' else "var(--blue-team)"
        team_name = "Rouge" if u['team_code'] == 'R' else "Bleue"

        unit_rows += f"""
            <tr style="{row_style}">
                <td>{i}</td>
                <td style="color: {team_color}; font-weight: bold;">{team_name}</td>
                <td>{u['type']}</td>
                <td>
                    {u['hp']:.0f} / {u['max_hp']:.0f}
                    <div class="progress-bg"><div class="progress-fill" style="width: {hp_percent}%; background: {('var(--success)' if u['is_alive'] else '#95a5a6')}"></div></div>
                </td>
                <td>({u['pos_x']:.1f}, {u['pos_y']:.1f})</td>
                <td class="{status_class}">{status_text}</td>
            </tr>"""

    content = f"""
        <h1>Rapport de Bataille en Temps Réel</h1>
        <div class="header-info">
            <div><strong>Tour:</strong> {data['turn']}</div>
            <div><strong>Temps de jeu:</strong> {data['in_game_time']}</div>
            <div><strong>IA Rouge:</strong> {data['ia1']}</div>
            <div><strong>IA Bleue:</strong> {data['ia2']}</div>
            <div><strong>Performance:</strong> {data['performance']} ({data['real_tps']} TPS)</div>
            <div><strong>Généré le:</strong> {now}</div>
        </div>

        <div class="stats-grid">
            {teams_content}
        </div>

        <h2>Liste Détaillée des Unités</h2>
        <table id="unitsTable">
            <thead>
                <tr>
                    <th onclick="sortTable('unitsTable', 0)">ID</th>
                    <th onclick="sortTable('unitsTable', 1)">Équipe</th>
                    <th onclick="sortTable('unitsTable', 2)">Type</th>
                    <th onclick="sortTable('unitsTable', 3)">Santé (HP)</th>
                    <th onclick="sortTable('unitsTable', 4)">Position</th>
                    <th onclick="sortTable('unitsTable', 5)">État</th>
                </tr>
            </thead>
            <tbody>
                {unit_rows}
            </tbody>
        </table>
    """
    return content


def _generate_lanchester_content(data, now):
    h = data['history']

    # Calcul des taux de pertes simplifiés
    red_losses = data['initial_red'] - data['final_red']
    blue_losses = data['initial_blue'] - data['final_blue']

    # Pour Lanchester, on regarde souvent le ratio d'efficacité
    # (Pertes Bleues / Effectif Rouge) vs (Pertes Rouges / Effectif Bleu)
    # C'est une simplification

    content = f"""
        <header>
            <h1>Analyse de Loi de Lanchester</h1>
            <div class="timestamp">Scénario: {data['scenario']}</div>
        </header>

        <div class="header-info">
            <div><strong>IA Rouge:</strong> {data['ia1']}</div>
            <div><strong>IA Bleue:</strong> {data['ia2']}</div>
            <div><strong>Vainqueur:</strong> {data['winner']}</div>
            <div><strong>Total Tours:</strong> {data['turn']}</div>
        </div>

        <div class="stats-summary-grid">
            <div class="stat-card">
                <div class="stat-label">Unités Rouges (Initial/Final)</div>
                <div class="stat-value">{data['initial_red']} &rarr; {data['final_red']}</div>
                <div style="color: var(--danger)">Pertes: {red_losses}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Unités Bleues (Initial/Final)</div>
                <div class="stat-value">{data['initial_blue']} &rarr; {data['final_blue']}</div>
                <div style="color: var(--danger)">Pertes: {blue_losses}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Rapport de Forces Initial</div>
                <div class="stat-value">{(data['initial_red'] / data['initial_blue']):.2f}</div>
                <small>Rouge / Bleu</small>
            </div>
        </div>

        <h2>Évolution des Effectifs</h2>
        <div style="height: 500px; margin-bottom: 40px;">
            <canvas id="lanchesterChart"></canvas>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const ctx = document.getElementById('lanchesterChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: {h['turns']},
                        datasets: [
                            {{
                                label: 'Unités Rouges ({data['ia1']})',
                                data: {h['red_units']},
                                borderColor: '#e74c3c',
                                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                                fill: true,
                                tension: 0.1
                            }},
                            {{
                                label: 'Unités Bleues ({data['ia2']})',
                                data: {h['blue_units']},
                                borderColor: '#3498db',
                                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                                fill: true,
                                tension: 0.1
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            x: {{
                                title: {{
                                    display: true,
                                    text: 'Tour de jeu'
                                }}
                            }},
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Nombre d\\'unités'
                                }}
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                position: 'top',
                            }},
                            title: {{
                                display: true,
                                text: 'Courbe d\\'attrition'
                            }}
                        }}
                    }}
                }});
            }});
        </script>

        <div class="export-info">
            La loi de Lanchester (notamment la loi carrée) suggère que la puissance de combat d'une force est proportionnelle 
            au carré de son effectif. Ces courbes permettent de vérifier si l'avantage numérique compense l'avantage qualitatif.
        </div>
    """
    return content


def _generate_lanchester_plot_content(data, now):
    results = data['results']
    x_labels = [r['n_blue_initial'] for r in results]
    red_final = [r['n_red_final'] for r in results]
    blue_final = [r['n_blue_final'] for r in results]

    # Calcul pour la loi carrée : (Initial^2 - Final^2)
    red_damage_taken = [max(0, r['n_red_initial'] ** 2 - r['n_red_final'] ** 2) for r in results]
    blue_damage_taken = [max(0, r['n_blue_initial'] ** 2 - r['n_blue_final'] ** 2) for r in results]

    rows = ""
    for r in results:
        winner_class = "winner-red" if r['winner'] == data['ia1'] else (
            "winner-blue" if r['winner'] == data['ia2'] else "winner-draw")
        rows += f"""
            <tr>
                <td>{r['n_red_initial']}</td>
                <td>{r['n_blue_initial']}</td>
                <td class="{winner_class}">{r['winner']}</td>
                <td>{r['n_red_final']}</td>
                <td>{r['n_blue_final']}</td>
                <td>{r['turns']}</td>
            </tr>
        """

    content = f"""
        <header>
            <h1>Vérification des Lois de Lanchester</h1>
            <div class="timestamp">Généré le {now}</div>
        </header>

        <div class="header-info">
            <div><strong>IA Rouge:</strong> {data['ia1']} ({data['unit_red']})</div>
            <div><strong>IA Bleue:</strong> {data['ia2']} ({data['unit_blue']})</div>
        </div>

        <div class="export-info">
            Ce rapport analyse la relation entre les effectifs initiaux et l'issue de la bataille 
            pour vérifier les modèles mathématiques de Lanchester.
        </div>

        <h2>Attrition Finale vs Effectif Initial Bleu</h2>
        <div style="height: 400px; margin-bottom: 40px;">
            <canvas id="attritionChart"></canvas>
        </div>

        <h2>Analyse de la Loi Carrée (Pertes au carré)</h2>
        <div style="height: 400px; margin-bottom: 40px;">
            <canvas id="squareLawChart"></canvas>
        </div>

        <h2>Données Brutes</h2>
        <table>
            <thead>
                <tr>
                    <th>Red Initial</th>
                    <th>Blue Initial</th>
                    <th>Vainqueur</th>
                    <th>Red Final</th>
                    <th>Blue Final</th>
                    <th>Tours</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const commonOptions = {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{ 
                            title: {{ display: true, text: 'Effectif Initial Bleu' }},
                            type: 'category'
                        }},
                        y: {{ beginAtZero: true }}
                    }}
                }};

                // Chart 1: Attrition
                new Chart(document.getElementById('attritionChart'), {{
                    type: 'line',
                    data: {{
                        labels: {x_labels},
                        datasets: [
                            {{
                                label: 'Red Restant',
                                data: {red_final},
                                borderColor: '#e74c3c',
                                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                                fill: true,
                                tension: 0.1
                            }},
                            {{
                                label: 'Blue Restant',
                                data: {blue_final},
                                borderColor: '#3498db',
                                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                                fill: true,
                                tension: 0.1
                            }}
                        ]
                    }},
                    options: {{
                        ...commonOptions,
                        plugins: {{ 
                            title: {{ display: true, text: 'Effectifs restants en fin de combat' }},
                            legend: {{ position: 'top' }}
                        }}
                    }}
                }});

                // Chart 2: Square Law
                new Chart(document.getElementById('squareLawChart'), {{
                    type: 'bar',
                    data: {{
                        labels: {x_labels},
                        datasets: [
                            {{
                                label: 'Pertes Rouges (Initial^2 - Final^2)',
                                data: {red_damage_taken},
                                backgroundColor: 'rgba(231, 76, 60, 0.5)'
                            }},
                            {{
                                label: 'Pertes Bleues (Initial^2 - Final^2)',
                                data: {blue_damage_taken},
                                backgroundColor: 'rgba(52, 152, 219, 0.5)'
                            }}
                        ]
                    }},
                    options: {{
                        ...commonOptions,
                        plugins: {{ 
                            title: {{ display: true, text: 'Vérification de la Loi Carrée' }},
                            legend: {{ position: 'top' }}
                        }}
                    }}
                }});
            }});
        </script>
    """
    return content
