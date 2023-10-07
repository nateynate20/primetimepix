import nfl_data_py

def fetch_nfl_teams(request):

    nfl_teams = nfl_data_py.import_team_desc()

    return JsonResponse({'nfl_teams': nfl_teams})
