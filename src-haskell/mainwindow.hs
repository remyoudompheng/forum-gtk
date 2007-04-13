-- Forum-gtk: fenêtre principale
-- Rémy Oudompheng, Mars 2007

module Main
    where

import Graphics.UI.Gtk
 
xml_menu :: IO String
xml_menu = do
    readFile "menu.xml"

main = create_window

create_window :: IO ()
create_window = do
    initGUI

    ui_manager <- uiManagerNew
    -- Contraction de la monade : xml_menu est de type IO String
    -- la fonction derrière est de type String -> IO foobar
    -- on fait IO String -> IO IO foobar -> IO foobar
    xml_menu >>= uiManagerAddUiFromString ui_manager

    action_group <- actionGroupNew "MainActions"
    
    actionGroupAddActions_FIXED action_group
        -- Menu Groupes
        [ActionEntry "GrpMenuAction" 
            "_Groupes"
            Nothing Nothing 
            Nothing
            (return ()),
        ActionEntry "GrpGotoAction" 
            "_Changer de groupe"
            Nothing (Just "g") 
            (Just "Aller dans un groupe donné")
            action_grpgoto_callback,
        ActionEntry "SubscribeAction" 
            "_Gérer les abonnements"
            Nothing (Just "L") 
            (Just "Gérer les abonnements aux groupes")
            action_subscribe_callback,
        ActionEntry "GrpSyncAction" 
            "_Rafraîchir la liste des groupes"
            Nothing Nothing 
            (Just "Recharger la liste des groupes du serveur")
            action_syncgroups_callback,
        -- Menu Sommaire
        ActionEntry "SumMenuAction" 
            "_Sommaire"
            Nothing Nothing 
            Nothing
            (return ()),
        ActionEntry "SumGotoAction" 
            "_Voir l'article numéro..."
            Nothing (Just "v") 
            (Just "Voir le n-ième article du groupe")
            action_sumgoto_callback,
        ActionEntry "OverviewAction" 
            "Voir le sommai_re du groupe..."
            Nothing (Just "r") 
            (Just "Voir le sommaire du groupe...")
            action_overview_callback,
        ActionEntry "NextUnreadAction" 
            "Article sui_vant"
            (Just stockGoForward) (Just "n") 
            (Just "Aller àu prochain article non lu")
            action_nextunread_callback,
        ActionEntry "ZapRepliesAction" 
            "Marquer la suite de la discussion comme lue"
            (Just stockMediaForward) (Just "<shift>K") 
            Nothing
            action_killreplies_callback,
        ActionEntry "ZapThreadAction" 
            "Marquer la discussion comme lue"
            (Just stockClear) (Just "<shift>J") 
            Nothing
            action_killthread_callback,
        ActionEntry "UnzapRepliesAction" 
            "Marquer la suite de la discussion comme non lue"
            (Just stockMediaRewind) (Just "<ctrl><shift>K") 
            Nothing
            action_unkillreplies_callback,
        ActionEntry "UnzapThreadAction" 
            "Marquer la discussion comme non lue"
            (Just stockUndelete) (Just "<ctrl><shift>J") 
            Nothing
            action_unkillthread_callback,
        ActionEntry "SaveTreeAsImageAction" 
            "Exporter l'arbre..."
            Nothing Nothing 
            (Just "Enregistre l'arbre de la discussion dans une image")
            action_savetreeasimage_callback,
        -- Menu Article
        ActionEntry "ArtMenuAction" 
            "_Articles"
            Nothing Nothing 
            Nothing
            (return ()),
        ActionEntry "NewAction" 
            "_Nouveau message"
            (Just stockNew) (Just "M") 
            (Just "Écrire un nouveau message")
            action_new_callback,
        ActionEntry "ReplyAction" 
            "_Répondre"
            (Just stockRedo) (Just "<shift>R") 
            (Just "Répondre à un message")
            action_reply_callback,
        ActionEntry "CancelAction" 
            "_Cancel"
            (Just stockDelete) (Just "e") 
            (Just "Effacer un message (cancel)")
            action_cancel_callback,
        ActionEntry "SupsedeAction" 
            "_Supersede"
            (Just stockStrikethrough) Nothing 
            (Just "Remplacer un message (supersede)")
            action_supsede_callback,
        ActionEntry "GotoParentAction" 
            "Aller au _parent"
            (Just stockGoUp) (Just "asciicircum") 
            (Just "Aller au message parent")
            action_goto_parent_callback,
        ActionEntry "MsgidGotoAction" 
            "Suivre le Ms_gId..."
            (Just stockJumpTo) Nothing 
            (Just "Voir un article donné par son Message-Id")
            action_msgidgoto_callback,
        ActionEntry "MsgViewRawAction" 
            "_Voir un article brut"
            Nothing (Just "<shift>V") 
            (Just "Voir l'article brut (tel qu'il est sur le serveur)")
            action_msgviewraw_callback,
        -- menu Historique
        ActionEntry "HistoryAction" 
            "_Historique"
            Nothing (Just "<shift>H") 
            (Just "Voir l'historique des messages consultés")
            action_history_callback,
        -- menu Programme
        ActionEntry "ProgMenuAction" 
            "_Programme"
            Nothing Nothing 
            Nothing
            (return ()),
        ActionEntry "QuitAction" 
            "_Quitter"
            (Just stockQuit) (Just "<control>Q") 
            (Just "Quitter le programme")
            action_quit_callback,
        ActionEntry "QuitKillAction" 
            "Quitter _sans sauver"
            (Just stockStop) (Just "<control><shift>Q") 
            (Just "Quitter le programme sans enregistrer les messages lus")
            action_quit_kill_callback]

    actionGroupAddToggleActions_FIXED action_group 
        [ToggleActionEntry "MsgRot13Action"
            "Transformée par _Rot13"
            (Just stockSortAscending) (Just "<shift>X")
            (Just "Afficher le message en rot13")
            action_rot13ify_callback False]
    uiManagerInsertActionGroup ui_manager action_group 0

    window <- windowNew 
    windowSetTitle window "Forum-GTK2Hs"
    windowSetDefaultSize window 1000 700
    -- backquote = notation infixe
    window `onDelete` action_quit_window_callback
    uiManagerGetAccelGroup ui_manager >>= windowAddAccelGroup window

    -- La grosse boîte
    vbox_big <- vBoxNew False 0
    window `containerAdd` vbox_big
    (Just menubar) <- uiManagerGetWidget ui_manager "/ui/menubar"
    boxPackStart vbox_big menubar PackNatural 0
    (Just toolbar) <- uiManagerGetWidget ui_manager "/ui/toolbar"
    boxPackStart vbox_big toolbar PackNatural 0

    -- le panneau à contis
    panel_big <- hPanedNew
    boxPackStart vbox_big panel_big PackGrow 0
 -- panel_big `panedAdd1` groupBuffer

    -- le panneau de droite
    panel_right <- vPanedNew
    panel_big `panedAdd2` panel_right
    set panel_right [ panedPosition := 250 ]
    
    -- le panneau sommaire
    panel_topright <- hPanedNew
    panel_right `panedAdd1` panel_topright
    -- panedAdd1 panel_topright summaryBuffer
    -- panedAdd2 panel_topright treeBuffer

    -- le panneau article
    -- panel_right `panedAdd2` articleBuffer
    
    -- la barre d'état
    status_bar <- statusbarNew
    boxPackStart vbox_big status_bar PackNatural 0

    widgetShowAll window
    
    mainGUI

action_grpgoto_callback = return ()

action_subscribe_callback = return ()

action_syncgroups_callback = return ()

action_sumgoto_callback = return ()

action_overview_callback = return ()

action_nextunread_callback = return ()

action_killreplies_callback = return ()

action_killthread_callback = return ()

action_unkillreplies_callback = return ()

action_unkillthread_callback = return ()

action_savetreeasimage_callback = return ()

action_new_callback = return ()

action_reply_callback = return ()

action_cancel_callback = return ()

action_supsede_callback = return ()

action_goto_parent_callback = return ()

action_msgidgoto_callback = return ()

action_msgviewraw_callback = return ()

action_rot13ify_callback = return ()

action_history_callback = return ()

action_quit_callback = return () 

action_quit_window_callback :: Event -> IO Bool
action_quit_window_callback ev = return True

action_quit_kill_callback = return ()

-- This is to fix non-exporting of ActionEntry types
data ActionEntry = ActionEntry {
       actionName        :: String,
       actionLabel       :: String,
       actionStockId     :: Maybe String,
       actionAccelerator :: Maybe String,
       actionTooltip     :: Maybe String,
       actionCallback    :: IO ()
}

data ToggleActionEntry = ToggleActionEntry {
       toggleActionName        :: String,
       toggleActionLabel       :: String,
       toggleActionStockId     :: Maybe String,
       toggleActionAccelerator :: Maybe String,
       toggleActionTooltip     :: Maybe String,
       toggleActionCallback    :: IO (),
       toggleActionIsActive    :: Bool
}

actionGroupAddActions_FIXED :: ActionGroup
 -> [ActionEntry] -- ^ @entries@ - a list of action descriptions
 -> IO ()
actionGroupAddActions_FIXED self entries =
  flip mapM_ entries $ \(ActionEntry name label stockId
                        accelerator tooltip callback) -> do
    action <- actionNew name label tooltip stockId
    onActionActivate action callback
    actionGroupAddActionWithAccel self action accelerator

actionGroupAddToggleActions_FIXED :: ActionGroup
 -> [ToggleActionEntry] -- ^ @entries@ - a list of toggle action descriptions
 -> IO ()
actionGroupAddToggleActions_FIXED self entries =
  flip mapM_ entries $ \(ToggleActionEntry name label stockId
                        accelerator tooltip callback isActive) -> do
    action <- toggleActionNew name label tooltip stockId
    toggleActionSetActive action isActive
    onActionActivate action callback
    actionGroupAddActionWithAccel self action accelerator
