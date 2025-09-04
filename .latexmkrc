use utf8;
use warnings;
use strict;
use JSON;
use Digest::MD5;
use Cwd;
use File::Spec::Functions qw(catfile);

binmode(STDOUT, ":encoding(UTF-8)");
binmode(STDERR, ":encoding(UTF-8)"); 

my $project_dir = getcwd();

my $figures_dir = catfile($project_dir, 'figuras');

sub findAllArchives {
    my $src = shift;
    my @svg_archives = ();

    if(-d $src) {
        @svg_archives = glob("$src/*.svg");
    } else {
        print "❌ O caminho não é um diretório ou não existe.\n";
        return ();
    }
    return @svg_archives;
}

sub getFileStatus {
    my @src = @_;
    my %hash_file_stats = ();

    foreach my $file (@src) {
        if (-e $file) {
            open(my $fh, '<:raw', $file) or do {
                print "❌ Erro ao abrir '$file': $!\n";
                next;
            };
            my $md5 = Digest::MD5->new->addfile($fh)->b64digest;
            close($fh);
            $hash_file_stats{$file} = {
                md5 => $md5,
                size => -s $file,
                to_convert => 1,
                to_delete => 0
            };
        } else {
            print "❌ Arquivo não encontrado: $file\n";
        }
    }
    return %hash_file_stats;
}

sub compare_file_hashes{
    print "Inside compare_file_hashes sub\n";
    my ($src_files_ref, $old_svg_cache_ref, $new_svg_cache_ref) = @_;
    my @src_files = @$src_files_ref;
    my %old_svg_cache = %$old_svg_cache_ref;
    my %new_svg_cache = %$new_svg_cache_ref;

    foreach my $file (@src_files){
        if (exists $old_svg_cache{$file} && $old_svg_cache{$file}{md5} eq $new_svg_cache{$file}{md5}){
            $new_svg_cache{$file}{to_convert} = 0;
        } else {
            $new_svg_cache{$file}{to_convert} = 1;
        }
        $new_svg_cache{$file}{to_delete} = 0;
    }

    foreach my $deleted_file (keys %old_svg_cache) {
        if (!exists $new_svg_cache{$deleted_file}) {
            $new_svg_cache{$deleted_file} = {
                %{$old_svg_cache{$deleted_file}},
                to_convert => 0,
                to_delete => 1
            };
        }
    }

    return %new_svg_cache;
}

my @svg_files = findAllArchives($figures_dir) or warn "❌Nenhum arquivo SVG encontrado no diretório: $figures_dir.\n";

my %file_status = getFileStatus(@svg_files) or warn "❌ Não foi possível obter o status dos arquivos SVG.\n";

print "\n📊 LOG DOS ARQUIVOS SVG:\n";
for my $file (sort keys %file_status) {
    print "Arquivo: $file\n";
    print "MD5: " . $file_status{$file}{md5} . "\n";
    print "Para converter: " . ($file_status{$file}{to_convert} ? "Sim" : "Não") . "\n";
}

my $json_text = JSON->new->utf8->encode(\%file_status);

my $cache_file = catfile($figures_dir, 'svg_cache.json');
print("Cache file check: " . -e $cache_file);
print "\n";
if(-e $cache_file){
    open(my $file_handle, '<:encoding(UTF-8)', $cache_file) or die "❌ Não foi possível ler o arquivo '$cache_file': $!";
    my $json_text_from_archive = do { local $/; <$file_handle> };
    close($file_handle) or die "❌ Não foi possível fechar o arquivo '$cache_file': $!";
    my $old_json_cache_file_ref = eval{JSON->new->decode($json_text_from_archive)};
    if($@){
        warn "❌ Erro ao decodificar o arquivo JSON '$cache_file': $@";
    } elsif ($old_json_cache_file_ref && ref($old_json_cache_file_ref) eq 'HASH') {
        %file_status = compare_file_hashes(\@svg_files, $old_json_cache_file_ref, \%file_status);
        $json_text = JSON->new->utf8->encode(\%file_status);
    }
}
open(my $file_handle, '>:encoding(UTF-8)', $cache_file) or die "❌ Não foi possível abrir o arquivo '$cache_file': $!";
print $file_handle $json_text;
close($file_handle) or die "❌ Não foi possível fechar o arquivo '$cache_file': $!";

print "✅ Cache criado/atualizado com sucesso em '$cache_file'.\n";

my $raw = system("python", ".\\lib\\auto_svg2tikz.py", $cache_file);
if ($raw == -1) {
    die "❌ Falha ao executar python: $!";
} elsif ($raw & 127) {
    warn sprintf "⚠️ Python terminou por sinal %d\n", ($raw & 127);
} else {
    my $exit = $raw >> 8;
    exit($exit) if $exit != 0;
    if ($exit == 0) {
        if (open(my $file_handle, "<:encoding(UTF-8)", $cache_file)){
            local $/;
            my $json_text_after = <$file_handle>;
            close($file_handle);
            my $new_json_cache_file_ref = eval{JSON->new->decode($json_text_after)};
            if($@){
                warn "❌ Erro ao decodificar o arquivo JSON '$cache_file' após a conversão: $@";
            } elsif ($new_json_cache_file_ref && ref($new_json_cache_file_ref) eq 'HASH') {
                %file_status = %{$new_json_cache_file_ref};
            }
        }
    }
}
#print "Não foi encontrada uma versão do python na máquina compatível com o template. Para download e instalação, visite: https://www.python.org\n";

my @files_to_remove = grep { $file_status{$_}{to_delete} // 0} keys %file_status;

if (@files_to_remove) {
    my $removed = unlink @files_to_remove or warn "❌ Não foi possível remover os arquivos: @files_to_remove: $!";
    if ($removed != @files_to_remove) {
        print "⚠️ Nenhum arquivo foi removido. Verifique se os arquivos existem e se você tem permissão para removê-los.\n";
    } else {
        warn "⚠️ Removidos $removed de ".scalar(@files_to_remove)." (parcial)\n";
    }
    delete @file_status{@files_to_remove};

    if (open(my $file_handle, '>:encoding(UTF-8)', $cache_file)) {
        my $json_text_updated = JSON->new->utf8->encode(\%file_status);
        print $file_handle $json_text_updated;
        close($file_handle) or warn "❌ Não foi possível fechar o arquivo '$cache_file': $!";
        print "✅ Cache atualizado após remoção em '$cache_file'.\n";
    } else {
        warn "❌ Não foi possível abrir o arquivo '$cache_file' para atualização após remoção: $!";
    }
}

print "\n🔍 Arquivos TikZ criados/atualizados com sucesso em '$figures_dir'.\n  ";

$bibtex_use = 1;

$lualatex = "lualatex -recorder -synctex=1 -shell-escape -interaction=nonstopmode -file-line-error";

$pdflatex = "pdflatex -recorder -synctex=1 -shell-escape -interaction=nonstopmode -file-line-error";

$pdf_mode = 1;

sub command_exists {
    my ($cmd) = @_;
    my $null = $^O eq 'MSWin32' ? 'NUL' : '/dev/null';
    my $rc = system("$cmd --version > $null 2>&1");
    return ($rc == 0);
}

if (command_exists('makeglossaries')) {
    add_cus_dep('glo','gls',0,'makeglossaries');
    sub makeglossaries {
        my ($base) = @_;
        my $rc = system("makeglossaries $base");
        return ($rc == 0) ? 1 : 0;
    }
} else {
    add_cus_dep('glo', 'gls', 0, 'makeglo2gls');
    sub makeglo2gls {
        my ($base) = @_;
        my $rc = system("makeindex -s '${base}'.ist -t '${base}'.glg -o '${base}'.gls '${base}'.glo");
        return ($rc == 0) ? 1 : 0;
    }
}

@default_files = ('documento.tex');
