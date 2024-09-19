import time
import json
import os
import glob

import pandas as pd

import streamlit as st
from streamlit.components.v1 import html
from streamlit_option_menu import option_menu

from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridUpdateMode, ColumnsAutoSizeMode
from st_aggrid.grid_options_builder import GridOptionsBuilder


def run():
    st.set_page_config(
        page_title="Transactions",
        page_icon="🚀",
        layout="wide"
    )
    # Function to load data, with conditional caching based on the checkbox

    def load_data(auto_refresh):
        if auto_refresh:
            @st.cache_data(ttl=60)
            def fetch_data():
                return get_data()

        else:
            def fetch_data():
                return get_data()

        return fetch_data()

    def get_data():
        my_path = os.getcwd()

        # To Get All Months CSV Files From Directory
        all_json_files = glob.glob(os.path.join(my_path, "Account*.json"))

        # Get File All File Names To Group Data BY Each Account
        file_names = [f.split("\\")[-1].split(".")[0] for f in all_json_files]

        # Create Emptry DF To Put all Data Into
        df = pd.DataFrame()

        file_index = 0

        # Concating All Data In Our DF
        for file_path in all_json_files:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Create Temp DataFrames
            temp_df = pd.DataFrame(data['net'])
            temp_df["Account"] = file_names[file_index]

            file_index += 1

            # Concat To The Final DF
            df = pd.concat([df, temp_df])

            target_columns = ["Account", "tradingsymbol", "quantity", "average_price",
                              "last_price", "pnl", "buy_quantity",
                              "sell_quantity", "sell_price"]
        

        return df[target_columns]

    def get_details_data():

        details_df = pd.read_json("transactions_details.json")
        details_df = details_df[["account_id", "tradingsymbol", "status"]]

        return details_df

    @st.cache_data
    def get_profit_by_account(df):
        groupped_df = df.groupby(["Account"])[["pnl", "quantity"]].sum()

        return groupped_df.reset_index()

    @st.experimental_dialog("Details About Account", width="large")
    def details_data(df, selected_account):

        
        st.subheader(f"Details About {selected_account}")

        filt = df["Account"] == selected_account

        dff = df[filt].copy()

        detials = dff[["tradingsymbol", "pnl"]]
        st.dataframe(detials, use_container_width=True)

        # ///// Detals

        selected_account = selected_account.split("/")[-1]

        details_df = get_details_data()
        filt = details_df["account_id"] == selected_account
        details_df_filt = details_df[filt]

        details_df_filt = details_df_filt[["tradingsymbol", "status"]]

        def highlight_cells(status):

            if status == "CANCELLED":
                color = "#FFECEC"
            elif status == "REJECTED":
                color = "#FFFCE7"
            else:
                color = "#E8F9EE"

            return f'background-color: {color}'

        styled_df = details_df_filt.style.applymap(
            highlight_cells, subset=['status'])

        st.dataframe(styled_df, use_container_width=True)
    # Initialize session state

    if 'selected_row' not in st.session_state:
        st.session_state.selected_row = None

    # Read Css Style File
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    side_bar_options_style = {
        "container": {"padding": "0!important", "background-color": '#121212', "border-radius": "0"},
        "icon": {"color": "#fff", "font-size": "18px"},
        "nav-link": {"color": "#fff", "font-size": "14px", "text-align": "left", "margin": "0px", "margin-bottom": "0px"},
        "nav-link-selected": {"background-color": "#1B9C85", "font-size": "15px", },
    }

    header = st.container()
    content = st.container()

    with st.sidebar:
        page = option_menu(
            menu_title=None,
            options=['Home', 'Account'],

            icons=['house-door-fill', "bank"],

            menu_icon="cast",
            default_index=0,
            styles=side_bar_options_style
        )

        # ***********************************
        # **********  Home Page  ************
        # ***********************************

        if page == "Home":
            st.write("***")
            auto_refresh = st.checkbox("Auto Refresh", False)

            manual_refresh_btn = st.button("Refresh")

            with header:
                st.write("")
                st.success(
                    f"**Last Update at**: **{time.strftime('%Y-%m-%d %H:%M')}**")

            with content:
                if auto_refresh:
                    st_autorefresh(interval=60 * 1000, key="dataframerefresh")

                df = load_data(auto_refresh)

                st.subheader(f'Total Profit: {df["pnl"].sum():,.2f}')

                df_table = GridOptionsBuilder.from_dataframe(
                    get_profit_by_account(df))

                df_table.configure_default_column(
                    editable=False, groupable=True, sortable=False, suppressMovable=False)

                df_table.configure_pagination(
                    enabled=True, paginationAutoPageSize=True, paginationPageSize=5)

                df_table.configure_selection(
                    selection_mode="single", use_checkbox=True, pre_selected_rows=[])

                # df_table.configure_grid_options(
                #     suppressColumnVirtualisation=True, enableRangeSelection=True)

                gridOptions = df_table.build()

                df_grid_output = AgGrid(
                    get_profit_by_account(df),
                    gridOptions=gridOptions,
                    GridUpdateMode=GridUpdateMode.SELECTION_CHANGED,
                    allow_unsafe_jscode=True,
                    fit_columns_on_grid_load=True,
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                    height=250,
                    custom_css={
                        "#gridToolBar": {
                            "padding-bottom": "0px !important",
                        },

                    }
                )

                # Check if a row is selected
                if df_grid_output is not None:
                    is_user_choose = len(
                        df_grid_output["selected_rows"])

                    if is_user_choose == 1:

                        if df_grid_output['selected_rows']:
                            selected_row = df_grid_output['selected_rows'][0]

                            # Only update the selected row without refreshing the entire page
                            if st.session_state.selected_row != selected_row:
                                st.session_state.selected_row = selected_row

                        if st.session_state.selected_row:
                            filter_by_account = df_grid_output["selected_rows"][0]["Account"]
                            details_data(df, filter_by_account)

        # ***********************************
        # **********  Sales Page  ***********
        # ***********************************

        if page == "Account":
            with content:
                st.write("")
                st.success(
                    f"**Last Update at**: **{time.strftime('%Y-%m-%d %H:%M')}**")


run()
