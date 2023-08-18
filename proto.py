import streamlit as st
import altair as alt
import pandas as pd

certificate_levels = [1,2,4,6,8]

def import_pseo_data(filepath):
    df = pd.read_csv(filepath,low_memory=False,dtype={'cipcode':str, 'industry':str, 'institution':str})
    # certificates only (get rid of degrees)
    df = df[df.degree_level.isin(certificate_levels)]

    agg_info = pd.read_csv("label_agg_level_pseo.csv")
    cip_info = pd.read_csv("label_cipcode.csv")
    ind_info = pd.read_csv("label_industry.csv")
    inst_info = pd.read_csv("label_institution.csv")
    deg_info = pd.read_csv("label_degree_level.csv")

    df = (
        df.merge(agg_info, on="agg_level_pseo", how="left", suffixes=("", "_agg"))
          .merge(cip_info, on="cipcode", how="left", suffixes=("", "_cip"))
          .merge(ind_info, on="industry", how="left", suffixes=("", "_ind"))
          .merge(inst_info, on="institution", how="left", suffixes=("", "_inst"))
          .merge(deg_info, on="degree_level", how="left", suffixes=("", "_deg"))
    )
    return df

# e is earnings data (how much are they making post grad)
dfe = import_pseo_data('pseoe_tx.csv')

# # f is flow data (where are they going to work. also includes unemployment rates)
# dff =  import_pseo_data('pseof_tx.csv')


st.set_page_config(
    page_title="Learner Earnings Explorer",
    page_icon="🤑")

st.title('🤑 Learner Earnings Explorer')
st.write("Select your institution to view earnings data from graduates of your certificate programs.")
st.markdown("_Powered by experimental [data from the US Census Bureau](https://lehd.ces.census.gov/data/pseo_experimental.html). Only supports Texas institutions at this time._")
grouped_data = dfe[dfe['agg_level_pseo'] == 46].groupby(
    ['label_inst', 'label', 'label_deg', 'grad_cohort'])[[c for c in dfe.columns if "earnings" in c]].sum()


institution = st.selectbox(
    'Institution',
    grouped_data.index.get_level_values(0).unique()
)


def make_chart(chart_data):
    chart = alt.Chart(chart_data)
    points = chart.mark_line(point=True).encode(
        x=alt.X('years_out', axis=alt.Axis(title='Years after Graduation', values=[1,5,10]), scale=alt.Scale(domain=(1, 10))),
        y=alt.Y('p50', axis=alt.Axis(title='Earnings, $')),
    ).properties(
        width=150,
        height=150
    )
    errorbars = chart.mark_errorband().encode(
        x=alt.X("years_out"),
        y=alt.Y("p25", title=''),
        y2=alt.Y2("p75", title=''),
    ).properties(
        width=150,
        height=150
    )
    layered = alt.layer(points, errorbars).facet(column=alt.Column('grad_cohort', title="Graduation Cohort"))
    return layered

n_displayed = 0
for cat in grouped_data.loc[institution].index.get_level_values(0).unique():
    certs = grouped_data.loc[institution].loc[cat].index.get_level_values(0).unique()
    data_displays = []
    for cert in certs:
        data = grouped_data.loc[institution].loc[cat].loc[cert]
        some_valid = (data[[c for c in data.columns if "status" in c]] == 1).any(axis=1)
        if some_valid.astype(int).sum() > 0:
            # filter out rows where all data is invalid or missing
            chart_data = data[some_valid][[c for c in data[some_valid] if 'status' not in c]].reset_index().melt(id_vars='grad_cohort')
            chart_data['years_out'] = chart_data['variable'].apply(lambda x: x.split('_')[0].replace('y','')).astype(int)
            chart_data['percentile'] = chart_data['variable'].apply(lambda x: x.split('_')[1])
            chart_data = chart_data.pivot(index=['grad_cohort','years_out'], columns='percentile', values='value')
            
            # drop rows that sum to 0
            chart_data = chart_data[chart_data.sum(axis=1) > 0]
            chart_data = chart_data.reset_index()

            data_displays.append((cert, make_chart(chart_data)))
    if data_displays:
        st.subheader(cat)
        for display in data_displays:
            st.markdown("**" + display[0] + "**")
            display[1]
            n_displayed += 1

if n_displayed == 0:
    st.write("Sorry, no data available for this institution.")